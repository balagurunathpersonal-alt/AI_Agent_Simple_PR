import os
import subprocess
from pathlib import Path

from google import genai
from google.genai import types


# ============================================================
# Gemini Configuration
# ============================================================

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)


# ============================================================
# Supported File Types
# ============================================================

SUPPORTED_EXTENSIONS = {
    # iOS / Apple
    ".swift",
    ".m",
    ".mm",
    ".h",
    ".plist",
    ".xcconfig",

    # Android
    ".kt",
    ".kts",
    ".java",
    ".xml",
    ".gradle",

    # Cross-platform mobile
    ".dart",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",

    # Backend / scripting
    ".py",
    ".go",
    ".rb",
    ".php",
    ".cs",
    ".cpp",
    ".c",

    # Web
    ".html",
    ".css",
    ".scss",

    # Data / configuration
    ".json",
    ".yaml",
    ".yml",
    ".toml",

    # Shell / automation
    ".sh",
    ".bash",
    ".zsh",

    # Database
    ".sql",

    # Documentation
    ".md",
}


# Files without extensions that may still be important
SUPPORTED_FILENAMES = {
    "Dockerfile",
    "Podfile",
    "Gemfile",
    "Fastfile",
    "Cartfile",
    "Makefile",
}


# ============================================================
# Helper Functions
# ============================================================

def is_supported_file(filepath: str) -> bool:
    """
    Determines whether a file should be considered for review.
    """

    path = Path(filepath)

    if path.name in SUPPORTED_FILENAMES:
        return True

    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def is_safe_path(filepath: str) -> bool:
    """
    Prevents the agent from attempting directory traversal.
    """

    if ".." in Path(filepath).parts:
        return False

    return True


# ============================================================
# Agent Tools
# ============================================================

def get_changed_files() -> list[str]:
    """
    Returns supported files changed in the current Git working tree.

    The agent should use this tool before reviewing code.
    """

    print("\n🔧 TOOL CALLED: get_changed_files()")

    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only"
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return [
            f"Git error: {result.stderr}"
        ]

    changed_files = result.stdout.splitlines()

    supported_files = [
        filepath
        for filepath in changed_files
        if is_supported_file(filepath)
    ]

    print(
        f"📁 Changed supported files: "
        f"{supported_files}"
    )

    return supported_files


def read_file(filepath: str) -> str:
    """
    Reads the contents of a repository file.

    Args:
        filepath:
            Relative path of the file inside the repository.

    Returns:
        File contents or an error message.
    """

    print(
        f"\n🔧 TOOL CALLED: "
        f"read_file({filepath})"
    )

    if not is_safe_path(filepath):
        return f"Access denied: invalid path {filepath}"

    if not os.path.exists(filepath):
        return f"File not found: {filepath}"

    if not os.path.isfile(filepath):
        return f"Not a file: {filepath}"

    if not is_supported_file(filepath):
        return f"Unsupported file type: {filepath}"

    try:
        with open(
            filepath,
            "r",
            encoding="utf-8"
        ) as file:
            return file.read()

    except UnicodeDecodeError:
        return (
            f"Unable to read {filepath}. "
            f"The file appears to be binary."
        )

    except Exception as error:
        return (
            f"Unable to read {filepath}. "
            f"Error: {str(error)}"
        )


def get_git_diff(filepath: str) -> str:
    """
    Returns the Git diff for a specific changed file.

    Args:
        filepath:
            Relative path of the changed file.

    Returns:
        Git diff for that file.
    """

    print(
        f"\n🔧 TOOL CALLED: "
        f"get_git_diff({filepath})"
    )

    if not is_safe_path(filepath):
        return f"Access denied: invalid path {filepath}"

    result = subprocess.run(
        [
            "git",
            "diff",
            "--",
            filepath
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return (
            f"Unable to retrieve diff for {filepath}. "
            f"Error: {result.stderr}"
        )

    if not result.stdout.strip():
        return f"No Git diff found for {filepath}"

    return result.stdout


# ============================================================
# Agent Prompt
# ============================================================

prompt = """
You are a senior software engineer performing a professional
code review.

You have strong expertise in:

iOS:
- Swift
- SwiftUI
- UIKit
- Objective-C
- async/await
- actors
- @MainActor
- ARC
- memory management
- XCTest / Swift Testing

Android:
- Kotlin
- Java
- Jetpack Compose
- Coroutines
- Flow
- Android architecture

Cross-platform:
- Flutter
- Dart
- React Native
- JavaScript
- TypeScript

General engineering:
- Clean Architecture
- MVVM
- SOLID
- security
- concurrency
- performance
- error handling
- testability
- maintainability


Your task is to review the changes currently present
in the Git working tree.


IMPORTANT WORKFLOW:

1. First call get_changed_files().

2. For every relevant changed file:

   - call get_git_diff(filepath)
   - understand exactly what changed

3. If additional context is required:

   - call read_file(filepath)

4. Review primarily the code introduced or modified
   by the current change.

5. Do not report unrelated problems that already existed
   unless the new change makes those problems significantly
   more dangerous.

6. Never invent files, functions, classes, APIs, or code.

7. Only make claims based on code you have actually inspected.


FOCUS AREAS:

- correctness
- crashes
- null / optional handling
- error handling
- concurrency
- thread safety
- memory management
- architecture
- security
- performance
- maintainability
- API misuse
- resource leaks
- state management
- lifecycle issues
- testability
- missing important tests


SEVERITY LEVELS:

CRITICAL
Security vulnerability, data corruption, major production
failure or highly probable crash affecting critical flows.

HIGH
Likely crash, serious concurrency problem, memory issue,
major architectural defect or incorrect business behaviour.

MEDIUM
Important maintainability, reliability, architecture or
performance problem.

LOW
Minor issue worth improving but not blocking.


OUTPUT FORMAT:

Provide the review using the following format:

SUMMARY

Briefly explain what changed and your overall assessment.


OVERALL RISK

LOW / MEDIUM / HIGH / CRITICAL


FILES REVIEWED

List every file you actually inspected.


FINDINGS

For each finding provide:

Severity:
Category:
File:
Title:
Explanation:
Why it matters:
Suggested fix:


TESTING RECOMMENDATIONS

Mention important test scenarios that should be added or
executed because of these changes.


FINAL RECOMMENDATION

Choose exactly one:

APPROVE
APPROVE_WITH_COMMENTS
REQUEST_CHANGES


Do not create findings merely to fill the report.

If the changes are good, say so.
"""


# ============================================================
# Run Agent
# ============================================================

response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[
            get_changed_files,
            get_git_diff,
            read_file
        ]
    )
)


# ============================================================
# Print Result
# ============================================================

print("\n")
print("=" * 70)
print("                    AI PR REVIEW AGENT")
print("=" * 70)
print()

print(response.text)

print()
print("=" * 70)