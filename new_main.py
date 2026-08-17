import os

from google import genai
from google.genai import types

from remote_git_pr_review import GitHubPRClient
from review_models import PRReviewResult


# ============================================================
# Configuration
# ============================================================

GITHUB_OWNER = "balagurunathpersonal-alt"
GITHUB_REPO = "AI_Agent_Simple_PR"
PULL_REQUEST_NUMBER = 2

GEMINI_MODEL = (
    "gemini-3.5-flash-lite"
)


# ============================================================
# Gemini
# ============================================================

client = genai.Client(
    api_key=os.environ[
        "GEMINI_API_KEY"
    ]
)


# ============================================================
# GitHub
# ============================================================

github = GitHubPRClient(
    owner=GITHUB_OWNER,
    repo=GITHUB_REPO,
    pull_request_number=(
        PULL_REQUEST_NUMBER
    ),
)


# ============================================================
# Agent Tools
# ============================================================

def get_pull_request() -> dict:

    return (
        github
        .get_pull_request()
    )


def get_pull_request_files() -> list[dict]:

    return (
        github
        .get_pull_request_files()
    )


def read_repository_file(
    filepath: str
) -> str:

    return (
        github
        .read_repository_file(
            filepath
        )
    )


# ============================================================
# Agent Prompt
# ============================================================

prompt = f"""
You are a senior software engineer performing a
professional GitHub pull request review.

Repository:

{GITHUB_OWNER}/{GITHUB_REPO}

Pull Request:

#{PULL_REQUEST_NUMBER}


AVAILABLE TOOLS

get_pull_request()

get_pull_request_files()

read_repository_file(filepath)


REQUIRED WORKFLOW

1. Call get_pull_request().

2. Understand the purpose and size
   of the pull request.

3. Call get_pull_request_files().

4. Inspect every relevant changed file.

5. Carefully inspect the GitHub patches.

6. When additional context is needed,
   call:

   read_repository_file(filepath)

7. Review primarily problems introduced
   or exposed by this pull request.


INLINE COMMENT REQUIREMENT

For every finding that refers to a
specific changed line:

Set line_number to the NEW-file line
number shown on the RIGHT side of the
pull request diff.

Only provide a line_number when you
are confident that the line exists
inside the PR diff.

Do NOT guess line numbers.

If a finding applies to the file or
architecture generally and does not
belong to one exact changed line:

Set line_number to null.


FOCUS AREAS

- correctness
- crashes
- error handling
- concurrency
- thread safety
- memory management
- architecture
- security
- performance
- lifecycle
- state management
- API misuse
- testability


IOS-SPECIFIC REVIEW

For Swift / iOS code also consider:

- optionals
- force unwraps
- unsafe casts

- ARC

- retain cycles

- weak / strong captures

- async / await

- Task lifecycle

- actor isolation

- @MainActor

- Sendable

- SwiftUI state ownership

- @State

- @StateObject

- @ObservedObject

- @Environment

- UIKit lifecycle

- structured concurrency

- cancellation


SEVERITY


CRITICAL

Security vulnerability,
data corruption,
catastrophic production problem.


HIGH

Likely crash,
incorrect behaviour,
serious concurrency,
memory,
security,
or architecture problem.


MEDIUM

Important reliability,
performance,
architecture,
maintainability,
or testability problem.


LOW

Useful but normally
non-blocking improvement.


REVIEW RULES

Never invent:

- code
- files
- APIs
- line numbers
- behaviours

Only report findings supported by
code that you inspected.

Do not create findings simply to make
the report longer.

If the PR is good, report no findings.

Testing recommendations should relate
specifically to this pull request.
"""


# ============================================================
# Run Agent
# ============================================================

print()
print("=" * 70)
print(
    "              STARTING PR REVIEW"
)
print("=" * 70)


response = (
    client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[
                get_pull_request,
                get_pull_request_files,
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
)


# ============================================================
# Parse
# ============================================================

review = (
    PRReviewResult
    .model_validate_json(
        response.text
    )
)


# ============================================================
# Console output
# ============================================================

def print_review(
    result: PRReviewResult
):

    print()
    print("=" * 70)
    print(
        "                  AI PR REVIEW"
    )
    print("=" * 70)

    print(
        f"\nSummary:\n"
        f"{result.pr_summary}"
    )

    print(
        "\nOverall Risk: "
        f"{result.overall_risk.value}"
    )

    print("\nFiles Reviewed:")

    for filepath in (
        result.files_reviewed
    ):
        print(
            f"- {filepath}"
        )

    print("\nFindings:")

    if not result.findings:

        print(
            "\n✅ No meaningful "
            "findings."
        )

    else:

        for index, finding in enumerate(
            result.findings,
            start=1
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
                f"   Fix: "
                f"{finding.suggested_fix}"
            )

    print(
        "\nTesting Recommendations:"
    )

    for test in (
        result.testing_recommendations
    ):

        print(
            f"- {test}"
        )

    print(
        "\nFinal Recommendation: "
        f"{result.final_recommendation.value}"
    )

    print()
    print("=" * 70)


# ============================================================
# Inline comment formatting
# ============================================================

def build_inline_comment(
    finding
) -> str:

    return (
        f"**🤖 AI Review "
        f"— {finding.severity.value}**\n\n"

        f"**{finding.title}**\n\n"

        f"{finding.explanation}\n\n"

        f"**Why it matters:** "
        f"{finding.why_it_matters}\n\n"

        f"**Suggested fix:** "
        f"{finding.suggested_fix}"
    )


# ============================================================
# Summary formatting
# ============================================================

def build_summary_comment(
    result: PRReviewResult
) -> str:

    comment = (
        "## 🤖 AI PR Review Summary\n\n"

        f"{result.pr_summary}\n\n"

        "### Overall Risk\n\n"

        f"**"
        f"{result.overall_risk.value}"
        f"**\n\n"

        "### Final Recommendation\n\n"

        f"**"
        f"{result.final_recommendation.value}"
        f"**\n\n"
    )

    if (
        result.testing_recommendations
    ):

        comment += (
            "### Testing Recommendations\n\n"
        )

        for test in (
            result.testing_recommendations
        ):

            comment += (
                f"- {test}\n"
            )

    comment += (
        "\n---\n"
        "_AI-generated review. "
        "Validate findings before "
        "making engineering decisions._"
    )

    return comment


# ============================================================
# Show result
# ============================================================

print_review(
    review
)


# ============================================================
# Human approval
# ============================================================

print(
    "\n⚠️ Nothing has been "
    "posted to GitHub yet."
)


approval = input(
    "\nPublish AI review "
    "to GitHub? [y/N]: "
)


if (
    approval
    .strip()
    .lower()
    == "y"
):

    print(
        "\nPublishing inline "
        "review comments..."
    )

    posted_count = 0
    skipped_count = 0

    for finding in (
        review.findings
    ):

        if (
            finding.line_number
            is None
        ):

            print(
                "\n⚠️ No exact line for:"
            )

            print(
                finding.title
            )

            skipped_count += 1

            continue

        comment = (
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
                    comment
                ),
            )
        )

        if success:

            posted_count += 1

        else:

            skipped_count += 1

    # Always add small summary
    summary = (
        build_summary_comment(
            review
        )
    )

    github.post_pull_request_comment(
        summary
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
        "\n✅ Nothing was "
        "published."
    )