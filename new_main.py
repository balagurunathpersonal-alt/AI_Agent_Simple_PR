import os

from google import genai
from google.genai import types

from github_pr_debug import GitHubPRDebugClient
from review_models_debug import PRReviewResult


# ============================================================
# CONFIGURATION
# ============================================================

# UPDATE THESE THREE VALUES

GITHUB_OWNER = "balagurunathpersonal-alt"
GITHUB_REPO = "AI_Agent_Simple_PR"
PULL_REQUEST_NUMBER = 2


GEMINI_MODEL = (
    "gemini-3.5-flash-lite"
)


# ============================================================
# CLIENTS
# ============================================================

gemini = genai.Client(
    api_key=os.environ[
        "GEMINI_API_KEY"
    ]
)


github = GitHubPRDebugClient(
    owner=GITHUB_OWNER,
    repo=GITHUB_REPO,
    pull_request_number=(
        PULL_REQUEST_NUMBER
    ),
)


# ============================================================
# AGENT TOOLS
# ============================================================

def get_pull_request() -> dict:
    """
    Get metadata for the pull request.
    """

    return github.get_pull_request()


def get_pull_request_files() -> list[dict]:
    """
    List reviewable files changed by the PR.
    """

    return (
        github
        .get_pull_request_files()
    )


def get_file_diff(
    filepath: str
) -> str:
    """
    Get the exact GitHub diff for one file.

    Args:
        filepath:
            Repository-relative path.
    """

    return (
        github
        .get_file_diff(
            filepath
        )
    )


def read_repository_file(
    filepath: str
) -> str:
    """
    Read the complete file at the PR head commit.

    Args:
        filepath:
            Repository-relative path.
    """

    return (
        github
        .read_repository_file(
            filepath
        )
    )


# ============================================================
# REVIEW PROMPT
# ============================================================

prompt = f"""
You are a highly critical senior Architect and code reviewer,
performing a GitHub pull request review.

Repository:

{GITHUB_OWNER}/{GITHUB_REPO}

Pull Request:

#{PULL_REQUEST_NUMBER}


AVAILABLE TOOLS

1. get_pull_request()

2. get_pull_request_files()

3. get_file_diff(filepath)

4. read_repository_file(filepath)


============================================================
MANDATORY REVIEW WORKFLOW
============================================================


STEP 1

You MUST call:

get_pull_request()

Verify that you are reviewing the intended PR.


STEP 2

You MUST call:

get_pull_request_files()

Identify every changed source code or configuration file.


STEP 3

For EVERY changed reviewable file, you MUST call:

get_file_diff(filepath)

Do not skip this step.

The GitHub diff is the primary source of truth
for determining what this pull request changed.


STEP 4

Inspect every added and modified line carefully.

Do not merely summarize the diff.

Perform an actual defect review.


STEP 5

If the diff alone is insufficient to determine
whether a change is correct, call:

read_repository_file(filepath)

Use the complete file to understand:

- surrounding implementation
- class responsibilities
- state
- dependencies
- concurrency context
- lifecycle
- calling patterns


============================================================
MANDATORY DEFECT CHECKLIST
============================================================


For EVERY changed code block, explicitly evaluate:

1. Can this change cause a runtime crash?

2. Can this change cause incorrect application behaviour?

3. Can an exception or error escape unexpectedly?

4. Can a nullable/optional value be accessed unsafely?

5. Does the change introduce unsafe type conversion?

6. Can the change create a race condition?

7. Can it mutate shared state unsafely?

8. Can it update UI state from an unsafe thread/actor?

9. Can it create a memory leak or retain cycle?

10. Can it leak credentials or sensitive information?

11. Can it bypass validation, authentication
    or authorization?

12. Can it introduce a performance regression?

13. Does it introduce behaviour that requires new tests?


============================================================
SWIFT / IOS MANDATORY CHECKS
============================================================


When the file contains Swift or Objective-C,
specifically inspect newly added or modified uses of:

- try!

- force unwrap !

- as!

- fatalError()

- preconditionFailure()

- implicitly unwrapped optionals

- Task

- Task.detached

- async / await

- MainActor

- @MainActor

- actor

- Sendable

- DispatchQueue

- weak self

- unowned self

- escaping closures

- delegates

- @State

- @StateObject

- @ObservedObject

- @Environment

- ObservableObject

- UIKit lifecycle methods


A newly introduced:

try!

force unwrap

or unsafe cast

MUST be treated as suspicious and evaluated
for possible runtime crash behaviour.


============================================================
IMPORTANT REVIEW BEHAVIOUR
============================================================


Do NOT assume code is correct merely because:

- it compiles
- it looks simple
- the diff is small


Do NOT ignore obvious unsafe constructs.

Do NOT fabricate findings.

Do NOT fabricate line numbers.

Do NOT invent code.

Every finding must be supported by code
you actually inspected.


============================================================
LINE NUMBER RULE
============================================================


For a finding tied to a specific changed line:

Set line_number to the NEW-file line number
on the RIGHT side of the GitHub diff.


Only assign a line number when you are confident
that the line is visible in the PR patch.


If the issue is architectural or file-wide:

line_number must be null.


============================================================
SEVERITY
============================================================


CRITICAL

Use when the change could cause:

- severe security breach
- major data corruption
- catastrophic system failure


HIGH

Use when the change could cause:

- likely runtime crash
- incorrect production behaviour
- serious concurrency defect
- serious memory defect
- significant security problem


MEDIUM

Use for:

- reliability problems
- architecture problems
- performance problems
- maintainability risks
- testability problems


LOW

Use for:

- legitimate non-blocking improvements


============================================================
FINAL DECISION
============================================================


REQUEST_CHANGES

Use when at least one finding should
reasonably block the PR.


APPROVE_WITH_COMMENTS

Use for valid but non-blocking concerns.


APPROVE

Use only when no meaningful problems
were identified.


Do not produce findings simply to avoid APPROVE.
"""


# ============================================================
# START
# ============================================================

print()
print("=" * 70)
print("          AI PR REVIEW - DEBUG VERSION")
print("=" * 70)


# ============================================================
# RUN AGENT
# ============================================================

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

        response_mime_type=(
            "application/json"
        ),

        response_schema=(
            PRReviewResult
        ),
    ),
)


# ============================================================
# RAW GEMINI OUTPUT
# ============================================================

print()
print("=" * 70)
print("RAW GEMINI RESPONSE")
print("=" * 70)

print(response.text)

print("=" * 70)


# ============================================================
# STRUCTURED RESULT
# ============================================================

review = (
    PRReviewResult
    .model_validate_json(
        response.text
    )
)


print()
print("=" * 70)
print("STRUCTURED REVIEW RESULT")
print("=" * 70)

print(
    review.model_dump_json(
        indent=2
    )
)

print("=" * 70)


# ============================================================
# HUMAN-FRIENDLY RESULT
# ============================================================

print()
print("=" * 70)
print("AI PR REVIEW")
print("=" * 70)

print(
    f"\nSummary:\n"
    f"{review.pr_summary}"
)

print(
    f"\nOverall Risk: "
    f"{review.overall_risk.value}"
)

print("\nFiles Reviewed:")

if review.files_reviewed:

    for filepath in (
        review.files_reviewed
    ):
        print(
            f"- {filepath}"
        )

else:

    print("- None")


print("\nFindings:")


if not review.findings:

    print(
        "\n✅ No meaningful "
        "findings detected."
    )

else:

    for index, finding in enumerate(
        review.findings,
        start=1,
    ):

        print()

        print(
            f"{index}. "
            f"[{finding.severity.value}] "
            f"{finding.title}"
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


print(
    "\nTesting Recommendations:"
)


if review.testing_recommendations:

    for recommendation in (
        review.testing_recommendations
    ):

        print(
            f"- {recommendation}"
        )

else:

    print("- None")


print(
    "\nFinal Recommendation: "
    f"{review.final_recommendation.value}"
)

print()
print("=" * 70)


# ============================================================
# INLINE COMMENT BUILDER
# ============================================================

def build_inline_comment(
    finding
) -> str:

    return (
        f"**🤖 AI Review "
        f"— {finding.severity.value}**\n\n"

        f"### {finding.title}\n\n"

        f"{finding.explanation}\n\n"

        f"**Why it matters:** "
        f"{finding.why_it_matters}\n\n"

        f"**Suggested fix:** "
        f"{finding.suggested_fix}"
    )


# ============================================================
# SUMMARY COMMENT BUILDER
# ============================================================

def build_summary_comment(
    result: PRReviewResult
) -> str:

    comment = (
        "## 🤖 AI PR Review Summary\n\n"

        "### Summary\n\n"

        f"{result.pr_summary}\n\n"

        "### Overall Risk\n\n"

        f"**"
        f"{result.overall_risk.value}"
        f"**\n\n"

        "### Findings\n\n"
    )


    if not result.findings:

        comment += (
            "✅ No meaningful "
            "findings identified.\n\n"
        )

    else:

        for index, finding in enumerate(
            result.findings,
            start=1,
        ):

            comment += (
                f"{index}. "
                f"**[{finding.severity.value}] "
                f"{finding.title}** "
                f"— `{finding.file}`"
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


    if result.testing_recommendations:

        for test in (
            result.testing_recommendations
        ):

            comment += (
                f"- {test}\n"
            )

    else:

        comment += "- None\n"


    comment += (
        "\n### Final Recommendation\n\n"

        f"**"
        f"{result.final_recommendation.value}"
        f"**\n\n"

        "---\n"

        "_AI-generated review. "
        "Validate findings before making "
        "engineering decisions._"
    )


    return comment


# ============================================================
# HUMAN APPROVAL
# ============================================================

print(
    "\n⚠️ Nothing has been "
    "posted to GitHub."
)


approval = input(
    "\nPublish this debug review "
    "to GitHub? [y/N]: "
)


if (
    approval.strip().lower()
    == "y"
):

    posted_count = 0

    skipped_count = 0


    # --------------------------------------------------------
    # Inline findings
    # --------------------------------------------------------

    for finding in (
        review.findings
    ):

        if (
            finding.line_number
            is None
        ):

            print()
            print(
                "⚠️ Finding has no "
                "specific diff line:"
            )

            print(
                finding.title
            )

            skipped_count += 1

            continue


        inline_comment = (
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
                    inline_comment
                ),
            )
        )


        if success:

            posted_count += 1

        else:

            skipped_count += 1


    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary_comment = (
        build_summary_comment(
            review
        )
    )


    github.post_pull_request_comment(
        summary_comment
    )


    print()
    print("=" * 70)

    print(
        f"Inline comments posted: "
        f"{posted_count}"
    )

    print(
        f"Inline comments skipped: "
        f"{skipped_count}"
    )

    print("=" * 70)


else:

    print(
        "\n✅ Nothing was published."
    )