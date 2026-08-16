import os

from google import genai
from google.genai import types


client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)


SAMPLE_CODE_DIRECTORY = "sample_code"


def list_swift_files() -> list[str]:
    """
    Lists all Swift files available in the sample project.

    Returns:
        A list containing Swift filenames.
    """

    print("\n🔧 TOOL CALLED: list_swift_files()")

    files = os.listdir(SAMPLE_CODE_DIRECTORY)

    swift_files = [
        file
        for file in files
        if file.endswith(".swift")
    ]

    return swift_files


def read_swift_file(filename: str) -> str:
    """
    Reads a Swift source file.

    Args:
        filename: Name of the Swift file.

    Returns:
        Contents of the requested Swift file.
    """

    print(
        f"\n🔧 TOOL CALLED: "
        f"read_swift_file({filename})"
    )

    file_path = os.path.join(
        SAMPLE_CODE_DIRECTORY,
        filename
    )

    if not os.path.exists(file_path):
        return f"File not found: {filename}"

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:
        return file.read()


prompt = """
You are a senior iOS Architect performing a code review.

Review the Swift project available to you.

You do NOT know which Swift files exist.

Use the available tools to:

1. Discover the Swift files.
2. Read the relevant files.
3. Understand relationships between the files.
4. Review the implementation.

Focus on meaningful issues involving:

- Swift correctness
- Swift concurrency
- SwiftUI
- memory management
- architecture
- crash risks
- performance
- maintainability

Do not invent files or code.

Only review code that you have actually inspected.

Provide:
- Summary
- Overall risk
- Important findings
- Recommended improvements
"""


response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[
            list_swift_files,
            read_swift_file
        ]
    )
)


print("\n================================")
print("        AI PROJECT REVIEW")
print("================================\n")

print(response.text)