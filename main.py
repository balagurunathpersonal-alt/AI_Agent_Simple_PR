import os

from google import genai
from google.genai import types

from remote_git_pr_review import GitHubPRClient


# ============================================================
# Configuration
# ============================================================

GITHUB_OWNER = "balagurunathpersonal-alt"
GITHUB_REPO = "AI_Agent_Simple_PR"
PULL_REQUEST_NUMBER = 1


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
# GitHub Client
# ============================================================

github = GitHubPRClient(
    owner=GITHUB_OWNER,
    repo=GITHUB_REPO,
    pull_request_number=(
        PULL_REQUEST_NUMBER
    ),
)


# ============================================================
# Agent tools
# ============================================================

def get_pull_request() -> dict:
    """
    Returns metadata about the GitHub
    pull request.
    """

    return github.get_pull_request()


def get_pull_request_files() -> list[dict]:
    """
    Returns relevant files changed
    by the pull request.
    """

    return (
        github
        .get_pull_request_files()
    )


def read_repository_file(
    filepath: str
) -> str:
    """
    Reads a repository file from
    the PR source commit.

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
# Agent Instructions
# ============================================================

prompt = f"""
You are a senior Architect
performing a professional GitHub
pull request review.


REPOSITORY

{GITHUB_OWNER}/{GITHUB_REPO}


PULL REQUEST

#{PULL_REQUEST_NUMBER}


YOUR AVAILABLE TOOLS

get_pull_request()

get_pull_request_files()

read_repository_file(filepath)


REQUIRED WORKFLOW


STEP 1

Call get_pull_request().

Understand:

- PR title
- description
- author
- source branch
- target branch
- number of changed files
- additions
- deletions


STEP 2

Call get_pull_request_files().

Inspect every relevant changed file.


STEP 3

Use the GitHub patch to understand
exactly what changed.


STEP 4

If the patch is insufficient or you
need surrounding implementation
context, call:

read_repository_file(filepath)


STEP 5

Review primarily problems introduced
or exposed by this PR.


DO NOT

- invent code
- invent files
- invent APIs
- make assumptions about code you
  have not inspected
- complain about unrelated legacy code
- create findings merely to make the
  report longer


FOCUS AREAS


CORRECTNESS

Look for:

- incorrect logic
- crashes
- force unwraps
- unsafe casts
- null handling
- unexpected state changes


CONCURRENCY

Look for:

- race conditions
- actor isolation problems
- MainActor violations
- unsafe async behaviour
- cancellation problems
- shared mutable state


MEMORY

Look for:

- retain cycles
- strong closure captures
- lifecycle problems
- leaked resources


ARCHITECTURE

Look for:

- layer violations
- business logic in UI
- excessive coupling
- poor dependency boundaries
- responsibilities placed in the
  wrong component


SECURITY

Look for:

- hardcoded secrets
- sensitive logging
- unsafe persistence
- insecure networking
- input validation problems


PERFORMANCE

Look for:

- unnecessary work
- repeated expensive operations
- blocking calls
- excessive rendering
- inefficient loops
- unnecessary allocations


TESTABILITY

Look for:

- important behaviour without tests
- missing error scenarios
- missing concurrency tests
- missing edge-case coverage


SEVERITY


CRITICAL

Security vulnerability,
data corruption,
major production outage,
or catastrophic behaviour.


HIGH

Likely crash,
incorrect production behaviour,
serious concurrency,
memory,
security,
or architectural problem.


MEDIUM

Meaningful reliability,
performance,
architecture,
maintainability,
or testability problem.


LOW

Useful improvement that normally
does not block merging.


OUTPUT FORMAT


# PR SUMMARY

Explain what this PR changes.


# OVERALL RISK

Choose:

LOW
MEDIUM
HIGH
CRITICAL


# FILES REVIEWED

List only files you actually inspected.


# FINDINGS

For each real finding:

## Finding N

Severity:

Category:

File:

Title:

Explanation:

Why it matters:

Suggested fix:


If there are no meaningful issues,
explicitly state:

No blocking findings identified.


# TESTING RECOMMENDATIONS

List tests specifically relevant
to this PR.


# FINAL RECOMMENDATION

Choose exactly one:

APPROVE

APPROVE_WITH_COMMENTS

REQUEST_CHANGES
"""


# ============================================================
# Run Agent
# ============================================================

print()
print("=" * 70)
print(
    "        STARTING AI PR REVIEW"
)
print("=" * 70)


response = (
    client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=(
            types
            .GenerateContentConfig(
                tools=[
                    get_pull_request,
                    get_pull_request_files,
                    read_repository_file,
                ]
            )
        ),
    )
)


review_text = response.text


# ============================================================
# Display Review
# ============================================================

print()
print("=" * 70)
print(
    "              AI PR REVIEW"
)
print("=" * 70)
print()

print(review_text)

print()
print("=" * 70)


# ============================================================
# Human Approval Gate
# ============================================================

print(
    "\n⚠️ Review has NOT been "
    "posted to GitHub."
)


approval = input(
    "\nPublish this review "
    "to GitHub? [y/N]: "
)


if (
    approval
    .strip()
    .lower()
    == "y"
):

    github_comment = f"""
## 🤖 AI PR Review

{review_text}

---

> AI-generated review.
> Validate findings before making
> engineering decisions.
"""

    github.post_pull_request_comment(
        github_comment
    )

else:

    print(
        "\n✅ Review was not "
        "published."
    )