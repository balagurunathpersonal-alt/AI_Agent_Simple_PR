import os

from google import genai
from google.genai import types

from code_analyzer_v2 import CodeAnalyzer
from github_pr_v2_fixed import GitHubPRClientV2
from review_models_v2 import (
    PRReviewResult,
    Recommendation,
    ReviewFinding,
    Severity,
)


# ============================================================
# CONFIGURATION
# ============================================================
GITHUB_OWNER = "balagurunathpersonal-alt"
GITHUB_REPO = "AI_Agent_Simple_PR"
PULL_REQUEST_NUMBER = 3


GEMINI_MODEL = "gemini-3.5-flash-lite"


# ============================================================
# CLIENTS
# ============================================================

gemini = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)


github = GitHubPRClientV2(
    owner=GITHUB_OWNER,
    repo=GITHUB_REPO,
    pull_request_number=PULL_REQUEST_NUMBER,
)


analyzer = CodeAnalyzer()


# ============================================================
# GEMINI TOOLS
# ============================================================

def get_pull_request() -> dict:
    """
    Returns metadata about the configured pull request.
    """

    return github.get_pull_request()


def get_pull_request_files() -> list[dict]:
    """
    Returns reviewable files changed by the pull request.
    """

    return github.get_pull_request_files()


def get_file_diff(
    filepath: str
) -> str:
    """
    Returns the GitHub diff for one changed file.

    Args:
        filepath:
            Repository-relative file path.
    """

    return github.get_file_diff(
        filepath
    )


def read_repository_file(
    filepath: str
) -> str:
    """
    Reads the complete file from the PR source commit.

    Args:
        filepath:
            Repository-relative file path.
    """

    return github.read_repository_file(
        filepath
    )


# ============================================================
# DETERMINISTIC ANALYSIS
# ============================================================

def run_static_analysis(
    changed_files: list[dict]
) -> list[ReviewFinding]:
    """
    Runs deterministic code checks against every
    supported changed file.

    This analysis runs independently of Gemini.

    Returns:
        List of static-analysis findings.
    """

    print()
    print("=" * 70)
    print("          RUNNING DETERMINISTIC ANALYSIS")
    print("=" * 70)

    findings: list[ReviewFinding] = []

    for file_data in changed_files:

        filepath = file_data["filename"]

        print()
        print(
            f"🔍 Static analysis: "
            f"{filepath}"
        )

        content = github.read_repository_file(
            filepath
        )

        if not content:
            print(
                f"⚠️ Unable to read "
                f"{filepath}"
            )
            continue

        file_findings = analyzer.analyze(
            filepath,
            content,
        )

        findings.extend(
            file_findings
        )

        print(
            f"   Findings: "
            f"{len(file_findings)}"
        )

    print()
    print(
        f"Total deterministic findings: "
        f"{len(findings)}"
    )

    return findings


# ============================================================
# GEMINI PROMPT
# ============================================================

prompt = f"""
You are a senior software engineer performing
a semantic GitHub pull request review.

Repository:

{GITHUB_OWNER}/{GITHUB_REPO}

Pull Request:

#{PULL_REQUEST_NUMBER}


You have access to these tools:

1. get_pull_request()

2. get_pull_request_files()

3. get_file_diff(filepath)

4. read_repository_file(filepath)


IMPORTANT ARCHITECTURE

A deterministic static analyzer is already running separately.

It checks obvious mechanical issues such as:

- try!
- as!
- fatalError
- preconditionFailure
- obvious unreachable code

Your job is to perform SEMANTIC review.

Do not depend on the static analyzer, but focus primarily
on issues requiring reasoning and context.


============================================================
MANDATORY WORKFLOW
============================================================

STEP 1

Call:

get_pull_request()

Understand:

- PR purpose
- title
- description
- source branch
- target branch
- change size


STEP 2

Call:

get_pull_request_files()

Identify every changed relevant file.


STEP 3

For EVERY changed relevant file call:

get_file_diff(filepath)

The GitHub diff is the primary source of truth
for determining what this PR introduced.


STEP 4

Inspect every added and modified code block.


STEP 5

If the diff does not provide enough surrounding context,
call:

read_repository_file(filepath)


============================================================
FOCUS AREAS
============================================================

CORRECTNESS

Look for:

- incorrect business logic
- incorrect control flow
- unexpected state changes
- incorrect API usage
- broken assumptions
- incorrect error handling


CONCURRENCY

Look for:

- race conditions
- MainActor violations
- actor isolation issues
- unsafe Task usage
- Task lifecycle problems
- cancellation problems
- shared mutable state
- thread-safety problems


MEMORY

Look for:

- retain cycles
- strong closure captures
- leaked resources
- lifecycle-related memory problems


ARCHITECTURE

Look for:

- incorrect layer dependencies
- excessive coupling
- business logic in UI
- inappropriate responsibilities
- poor dependency boundaries
- regressions in architecture


SECURITY

Look for:

- secrets
- API keys
- passwords
- sensitive logging
- unsafe persistence
- insecure networking
- missing validation
- authorization bypass


PERFORMANCE

Look for:

- unnecessary expensive work
- blocking calls
- excessive rendering
- unnecessary allocations
- repeated network requests
- inefficient loops


TESTABILITY

Look for:

- behavior changes without tests
- missing error tests
- missing concurrency tests
- missing edge cases
- difficult-to-test dependencies


============================================================
IOS / SWIFT SPECIFIC REVIEW
============================================================

For Swift and Objective-C inspect:

- async / await
- Task
- Task.detached
- @MainActor
- actors
- Sendable
- ARC
- weak self
- unowned self
- escaping closures
- delegates
- SwiftUI state ownership
- @State
- @StateObject
- @ObservedObject
- @Environment
- ObservableObject
- UIKit lifecycle


============================================================
FINDING RULES
============================================================

Do not invent:

- files
- code
- functions
- classes
- APIs
- line numbers
- behavior


Only create a finding when supported by code you inspected.


For every finding:

source MUST be:

AI_REVIEW


If a finding refers to an exact changed line:

Provide the NEW-file RIGHT-side line number.


If the issue is architectural or file-wide:

line_number must be null.


Do not create findings just to make the report longer.


If no semantic issues are found:

return zero AI findings.


============================================================
SEVERITY
============================================================

CRITICAL

Use when the PR could cause:

- severe security breach
- major data corruption
- catastrophic production failure


HIGH

Use when the PR could cause:

- likely runtime crash
- incorrect production behavior
- serious concurrency issue
- major memory issue
- major architecture problem
- major security problem


MEDIUM

Use for:

- reliability problems
- maintainability risks
- architecture concerns
- performance problems
- testability issues


LOW

Use for:

- legitimate non-blocking improvements
"""


# ============================================================
# FETCH PR DATA
# ============================================================

print()
print("=" * 70)
print("                    PR REVIEW V2")
print("=" * 70)


pr = github.get_pull_request()


if "error" in pr:

    print()
    print("❌ Unable to retrieve PR.")
    print(pr["error"])

    raise SystemExit(1)


changed_files = github.get_pull_request_files()


print()
print("=" * 70)
print("                    PR INFORMATION")
print("=" * 70)

print(
    f"PR Number: "
    f"#{pr.get('number')}"
)

print(
    f"Title: "
    f"{pr.get('title')}"
)

print(
    f"Author: "
    f"{pr.get('author')}"
)

print(
    f"Source Branch: "
    f"{pr.get('source_branch')}"
)

print(
    f"Target Branch: "
    f"{pr.get('target_branch')}"
)

print(
    f"Changed Files: "
    f"{pr.get('changed_files')}"
)

print(
    f"Additions: "
    f"{pr.get('additions')}"
)

print(
    f"Deletions: "
    f"{pr.get('deletions')}"
)


print()
print("Reviewable files:")

for file_data in changed_files:

    print(
        f"- {file_data['filename']}"
    )


# ============================================================
# STATIC ANALYSIS
# ============================================================

static_findings = run_static_analysis(
    changed_files
)


# ============================================================
# GEMINI SEMANTIC REVIEW
# ============================================================

print()
print("=" * 70)
print("               RUNNING GEMINI REVIEW")
print("=" * 70)


response = gemini.models.generate_content(
    model=GEMINI_MODEL,
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[
            get_pull_request,
            get_pull_request_files,
            get_file_diff,
            read_repository_file,
        ],

        response_mime_type="application/json",

        response_schema=PRReviewResult,
    ),
)


# ============================================================
# PARSE GEMINI RESULT
# ============================================================

ai_review = PRReviewResult.model_validate_json(
    response.text
)


print()
print("=" * 70)
print("                RAW AI REVIEW RESULT")
print("=" * 70)

print(
    ai_review.model_dump_json(
        indent=2
    )
)


# ============================================================
# MERGE STATIC + AI FINDINGS
# ============================================================

all_findings: list[ReviewFinding] = []

all_findings.extend(
    static_findings
)

all_findings.extend(
    ai_review.findings
)


# ============================================================
# DEDUPLICATE FINDINGS
# ============================================================

unique_findings: list[
    ReviewFinding
] = []

seen = set()


for finding in all_findings:

    key = (
        finding.file,
        finding.line_number,
        finding.category.lower(),
        finding.title.lower(),
    )

    if key in seen:
        continue

    seen.add(key)

    unique_findings.append(
        finding
    )


# ============================================================
# CALCULATE FINAL RISK
# ============================================================

def calculate_risk(
    findings: list[ReviewFinding]
) -> Severity:

    severities = {
        finding.severity
        for finding in findings
    }

    if Severity.CRITICAL in severities:

        return Severity.CRITICAL

    if Severity.HIGH in severities:

        return Severity.HIGH

    if Severity.MEDIUM in severities:

        return Severity.MEDIUM

    return Severity.LOW


overall_risk = calculate_risk(
    unique_findings
)


# ============================================================
# CALCULATE FINAL RECOMMENDATION
# ============================================================

def calculate_recommendation(
    findings: list[ReviewFinding]
) -> Recommendation:

    for finding in findings:

        if finding.severity in {
            Severity.CRITICAL,
            Severity.HIGH,
        }:

            return (
                Recommendation
                .REQUEST_CHANGES
            )

    if findings:

        return (
            Recommendation
            .APPROVE_WITH_COMMENTS
        )

    return Recommendation.APPROVE


final_recommendation = (
    calculate_recommendation(
        unique_findings
    )
)


# ============================================================
# FILES REVIEWED
# ============================================================

files_reviewed = list(
    {
        file_data["filename"]
        for file_data in changed_files
    }
)


# ============================================================
# BUILD FINAL REVIEW
# ============================================================

final_review = PRReviewResult(

    pr_summary=(
        ai_review.pr_summary
    ),

    overall_risk=(
        overall_risk
    ),

    files_reviewed=(
        files_reviewed
    ),

    findings=(
        unique_findings
    ),

    testing_recommendations=(
        ai_review
        .testing_recommendations
    ),

    final_recommendation=(
        final_recommendation
    ),
)


# ============================================================
# PRINT FINAL REVIEW
# ============================================================

print()
print("=" * 70)
print("                   FINAL PR REVIEW")
print("=" * 70)


print()
print("Summary:")

print(
    final_review.pr_summary
)


print()
print(
    "Overall Risk: "
    f"{final_review.overall_risk.value}"
)


print()
print("Files Reviewed:")


if final_review.files_reviewed:

    for filepath in (
        final_review.files_reviewed
    ):

        print(
            f"- {filepath}"
        )

else:

    print("- None")


print()
print("Findings:")


if not final_review.findings:

    print()
    print(
        "✅ No meaningful findings."
    )


else:

    for index, finding in enumerate(
        final_review.findings,
        start=1,
    ):

        print()

        print(
            f"{index}. "
            f"[{finding.severity.value}] "
            f"{finding.title}"
        )

        print(
            f"   Source: "
            f"{finding.source.value}"
        )

        print(
            f"   Category: "
            f"{finding.category}"
        )

        print(
            f"   File: "
            f"{finding.file}"
        )

        print(
            f"   Line: "
            f"{finding.line_number}"
        )

        print(
            f"   Explanation: "
            f"{finding.explanation}"
        )

        print(
            f"   Why it matters: "
            f"{finding.why_it_matters}"
        )

        print(
            f"   Suggested fix: "
            f"{finding.suggested_fix}"
        )


print()
print(
    "Testing Recommendations:"
)


if (
    final_review
    .testing_recommendations
):

    for recommendation in (
        final_review
        .testing_recommendations
    ):

        print(
            f"- {recommendation}"
        )

else:

    print("- None")


print()
print(
    "Final Recommendation: "
    f"{final_review.final_recommendation.value}"
)


print()
print("=" * 70)


# ============================================================
# INLINE COMMENT FORMATTER
# ============================================================

def build_inline_comment(
    finding: ReviewFinding
) -> str:

    return (
        f"**🤖 AI PR Review "
        f"— {finding.severity.value}**\n\n"

        f"**Source:** "
        f"{finding.source.value}\n\n"

        f"### {finding.title}\n\n"

        f"{finding.explanation}\n\n"

        f"**Why it matters:** "
        f"{finding.why_it_matters}\n\n"

        f"**Suggested fix:** "
        f"{finding.suggested_fix}"
    )


# ============================================================
# SUMMARY COMMENT FORMATTER
# ============================================================

def build_summary_comment(
    review: PRReviewResult
) -> str:

    comment = (
        "## 🤖 AI PR Review\n\n"

        "### Summary\n\n"

        f"{review.pr_summary}\n\n"

        "### Overall Risk\n\n"

        f"**"
        f"{review.overall_risk.value}"
        f"**\n\n"

        "### Findings\n\n"
    )


    if not review.findings:

        comment += (
            "✅ No meaningful findings.\n\n"
        )

    else:

        for index, finding in enumerate(
            review.findings,
            start=1,
        ):

            comment += (
                f"{index}. "
                f"**[{finding.severity.value}] "
                f"{finding.title}**\n"
            )

            comment += (
                f"   - Source: "
                f"`{finding.source.value}`\n"
            )

            comment += (
                f"   - File: "
                f"`{finding.file}`"
            )

            if (
                finding.line_number
                is not None
            ):

                comment += (
                    f":{finding.line_number}"
                )

            comment += "\n"


    comment += (
        "\n### Testing Recommendations\n\n"
    )


    if review.testing_recommendations:

        for recommendation in (
            review
            .testing_recommendations
        ):

            comment += (
                f"- {recommendation}\n"
            )

    else:

        comment += "- None\n"


    comment += (
        "\n### Final Recommendation\n\n"

        f"**"
        f"{review.final_recommendation.value}"
        f"**\n\n"

        "---\n\n"

        "_AI-generated review. "
        "Validate findings before making "
        "engineering decisions._"
    )


    return comment


# ============================================================
# HUMAN APPROVAL
# ============================================================

print()
print(
    "⚠️ Nothing has been posted "
    "to GitHub yet."
)


approval = input(
    "\nPublish V2 review "
    "to GitHub? [y/N]: "
)


# ============================================================
# PUBLISH
# ============================================================

if (
    approval
    .strip()
    .lower()
    == "y"
):

    posted = 0
    skipped = 0


    print()
    print("=" * 70)
    print(
        "                PUBLISHING REVIEW"
    )
    print("=" * 70)


    for finding in (
        final_review.findings
    ):

        if (
            finding.line_number
            is None
        ):

            print()
            print(
                "⚠️ Skipping inline comment "
                "because no exact diff line exists:"
            )

            print(
                f"   {finding.title}"
            )

            skipped += 1

            continue


        comment_body = (
            build_inline_comment(
                finding
            )
        )


        success = (
            github
            .post_inline_review_comment(
                filepath=(
                    finding.file
                ),

                line_number=(
                    finding.line_number
                ),

                comment_body=(
                    comment_body
                ),
            )
        )


        if success:

            print(
                f"✅ Posted inline: "
                f"{finding.file}:"
                f"{finding.line_number}"
            )

            posted += 1

        else:

            print(
                f"⚠️ Could not post inline: "
                f"{finding.file}:"
                f"{finding.line_number}"
            )

            skipped += 1


    summary_comment = (
        build_summary_comment(
            final_review
        )
    )


    summary_success = (
        github
        .post_pull_request_comment(
            summary_comment
        )
    )


    print()
    print("=" * 70)

    print(
        f"Inline comments posted: "
        f"{posted}"
    )

    print(
        f"Inline comments skipped: "
        f"{skipped}"
    )

    print(
        f"Summary posted: "
        f"{summary_success}"
    )

    print("=" * 70)


else:

    print()
    print(
        "✅ Nothing was published."
    )