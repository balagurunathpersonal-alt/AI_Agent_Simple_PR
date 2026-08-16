import os

from google import genai
from google.genai import types


client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)


def read_swift_file(filename: str) -> str:
    """
    Reads a Swift source file from the sample_code directory.

    Args:
        filename: Name of the Swift file to read.

    Returns:
        Contents of the Swift file.
    """

    print(f"\n🔧 TOOL CALLED: read_swift_file({filename})")

    file_path = os.path.join(
        "sample_code",
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
Review ProfileViewModel.swift.

You are a senior iOS Architect.

Do not guess the contents of the file.

Use the available tool to read the Swift file before reviewing it.

Focus on:
- Swift correctness
- concurrency
- memory management
- architecture
- crash risks
- maintainability

Explain the important findings clearly.
"""


response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[read_swift_file]
    )
)


print("\n==============================")
print("       AI CODE REVIEW")
print("==============================\n")

print(response.text)