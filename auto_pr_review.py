import os
from pathlib import Path

import requests
from google import genai
from google.genai import types


# ============================================================
# Configuration
# ============================================================

GITHUB_API_URL = "https://api.github.com"

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]


client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# Repository Configuration
# ============================================================

# Change these values to your repository
GITHUB_OWNER = "balagurunathpersonal-alt"
GITHUB_REPO = "AI_Agent_Simple_PR"

# Change this to the PR you want to review
PULL_REQUEST_NUMBER = 1


# ============================================================
# Supported File Types
# ============================================================

SUPPORTED_EXTENSIONS = {
    ".swift",
    ".m",
    ".mm",
    ".h",
    ".plist",
    ".xcconfig",

    ".kt",
    ".kts",
    ".java",
    ".xml",
    ".gradle",

    ".dart",

    ".js",
    ".jsx",
    ".ts",
    ".tsx",

    ".py",
    ".go",
    ".rb",
    ".php",
    ".cs",
    ".cpp",
    ".c",

    ".html",
    ".css",
    ".scss",

    ".json",
    ".yaml",
    ".yml",
    ".toml",

    ".sh",
    ".bash",
    ".zsh",

    ".sql",

    ".md",
}


SUPPORTED_FILENAMES = {
    "Dockerfile",
    "Podfile",
    "Gemfile",
    "Fastfile",
    "Cartfile",
    "Makefile",
}


# ============================================================
# GitHub Helpers
# ============================================================

def github_headers() -> dict:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
    }


def is_supported_file(filepath: str) -> bool:
    path = Path(filepath)

    if path.name in SUPPORTED_FILENAMES:
        return True

    return path.suffix.lower() in SUPPORTED_EXTENSIONS


# ============================================================
# Agent Tool 1
# Get PR Details
# ============================================================

def get_pull_request() -> dict:
    """
    Gets information about the configured GitHub pull request.

    Returns:
        Pull request metadata including title, description,
        source branch and target branch.
    """

    print("\n🔧 TOOL CALLED: get_pull_request()")

    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/pulls/"
        f"{PULL_REQUEST_NUMBER}"
    )

    response = requests.get(
        url,
        headers=github_headers(),
        timeout=30,
    )

    if response.status_code != 200:
        return {
            "error": (
                f"GitHub returned "
                f"{response.status_code}: "
                f"{response.text}"
            )
        }

    data = response.json()

    return {
        "number": data["number"],
        "title": data["title"],
        "description": data.get("body") or "",
        "state": data["state"],
        "author": data["user"]["login"],
        "source_branch": data["head"]["ref"],
        "target_branch": data["base"]["ref"],
        "commits": data["commits"],
        "changed_files": data["changed_files"],
        "additions": data["additions"],
        "deletions": data["deletions"],
    }


# ============================================================
# Agent Tool 2
# Get PR Changed Files
# ============================================================

def get_pull_request_files() -> list[dict]:
    """
    Gets supported files changed in the configured pull request.

    Returns:
        Changed files including filename, status and patch.
    """

    print("\n🔧 TOOL CALLED: get_pull_request_files()")

    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/pulls/"
        f"{PULL_REQUEST_NUMBER}/files"
    )

    response = requests.get(
        url,
        headers=github_headers(),
        params={
            "per_page": 100
        },
        timeout=30,
    )

    if response.status_code != 200:
        return [
            {
                "error": (
                    f"GitHub returned "
                    f"{response.status_code}: "
                    f"{response.text}"
                )
            }
        ]

    files = response.json()

    reviewable_files = []

    for file in files:

        filename = file["filename"]

        if not is_supported_file(filename):
            continue

        reviewable_files.append(
            {
                "filename": filename,
                "status": file["status"],
                "additions": file["additions"],
                "deletions": file["deletions"],
                "changes": file["changes"],

                # GitHub often provides the textual diff here.
                "patch": file.get("patch", ""),
            }
        )

    print(
        f"📁 Reviewable PR files: "
        f"{len(reviewable_files)}"
    )

    return reviewable_files


# ============================================================
# Agent Tool 3
# Read Repository File
# ============================================================

def read_repository_file(
    filepath: str
) -> str:
    """
    Reads the current contents of a file from the PR source branch.

    Args:
        filepath:
            Repository-relative path of the file.

    Returns:
        File contents.
    """

    print(
        f"\n🔧 TOOL CALLED: "
        f"read_repository_file({filepath})"
    )

    if ".." in Path(filepath).parts:
        return "Access denied: invalid file path"

    pr_url = (
        f"{GITHUB_API_URL}/repos/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/pulls/"
        f"{PULL_REQUEST_NUMBER}"
    )

    pr_response = requests.get(
        pr_url,
        headers=github_headers(),
        timeout=30,
    )

    if pr_response.status_code != 200:
        return (
            "Unable to retrieve PR branch information."
        )

    pr_data = pr_response.json()

    source_branch = pr_data["head"]["ref"]

    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/contents/"
        f"{filepath}"
    )

    response = requests.get(
        url,
        headers=github_headers(),
        params={
            "ref": source_branch
        },
        timeout=30,
    )

    if response.status_code != 200:
        return (
            f"Unable to read {filepath}. "
            f"GitHub returned "
            f"{response.status_code}."
        )

    data = response.json()

    download_url = data.get("download_url")

    if not download_url:
        return (
            f"No downloadable content found "
            f"for {filepath}"
        )

    file_response = requests.get(
        download_url,
        headers=github_headers(),
        timeout=30,
    )

    if file_response.status_code != 200:
        return (
            f"Unable to download {filepath}"
        )

    return file_response.text


# ============================================================
# Prompt
# ============================================================

prompt = f"""
You are a senior Architect performing a professional
GitHub pull request review.

Repository:

{GITHUB_OWNER}/{GITHUB_REPO}

Pull Request:

#{PULL_REQUEST_NUMBER}


You have access to GitHub tools.


REQUIRED WORKFLOW:

1. Call get_pull_request() first.

2. Understand:

   - PR title
   - PR description
   - source branch
   - target branch
   - approximate size of the change

3. Call get_pull_request_files().

4. Review every relevant changed source/configuration file.

5. Use the patch returned by GitHub to understand exactly
   what changed.

6. If a patch does not provide enough context,
   call read_repository_file(filepath).

7. Review primarily problems introduced by the pull request.

8. Do not report unrelated legacy problems unless the
   new changes make them relevant.

9. Never invent code.

10. Only report issues based on code you actually inspected.


FOCUS ON:
- architecture
- correctness
- crash risks
- optional/null handling
- error handling
- concurrency
- thread safety
- memory management
- architecture
- state management
- lifecycle issues
- security
- performance
- API misuse
- maintainability
- testability
- missing important tests


SEVERITY:

CRITICAL
Security vulnerability, major data corruption,
critical production failure.

HIGH
Likely crash, incorrect behaviour, serious concurrency,
memory or architectural problem.

MEDIUM
Important reliability, maintainability, architecture
or performance problem.

LOW
Useful improvement but not normally blocking.


OUTPUT FORMAT:


PR SUMMARY

Explain what the pull request appears to change.


OVERALL RISK

LOW / MEDIUM / HIGH / CRITICAL


FILES REVIEWED

List files actually inspected.


FINDINGS

For every finding:

Severity:
Category:
File:
Title:
Explanation:
Why it matters:
Suggested fix:


TESTING RECOMMENDATIONS

List important tests related to this PR.


FINAL RECOMMENDATION

Choose exactly one:

APPROVE
APPROVE_WITH_COMMENTS
REQUEST_CHANGES

COMMENTS:

add comments for the PR author align with the FINAL RECOMMENDATION. Don't add phrase that the PR is handled using AI. Need detailed comments


Do not invent findings just to produce a longer review.

If the PR is good, say so clearly. 
"""


# ============================================================
# Run Gemini Agent
# ============================================================

response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[
            get_pull_request,
            get_pull_request_files,
            read_repository_file,
        ]
    ),
)


# ============================================================
# Result
# ============================================================

print("\n")
print("=" * 70)
print("                   GITHUB PR REVIEW")
print("=" * 70)
print()

print(response.text)

print()
print("=" * 70)