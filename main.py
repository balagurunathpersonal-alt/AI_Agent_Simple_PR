import os
import json
from google import genai

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

swift_code = """
final class ProfileViewModel: ObservableObject {

    @Published var username: String = ""

    func loadProfile() {
        Task {
            let profile = await fetchProfile()
            self.username = profile.name
        }
    }

    private func fetchProfile() async -> Profile {
        try! await Task.sleep(for: .seconds(1))

        return Profile(
            name: "Balagurunath"
        )
    }
}
"""

prompt = f"""
You are a senior iOS Architect.

Review the Swift code below.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "summary": "short review summary",
  "overall_risk": "LOW | MEDIUM | HIGH | CRITICAL",
  "recommendation": "APPROVE | APPROVE_WITH_COMMENTS | REQUEST_CHANGES",
  "findings": [
    {{
      "severity": "LOW | MEDIUM | HIGH | CRITICAL",
      "category": "Concurrency | Memory | Correctness | Architecture | Performance | Security | Testing",
      "title": "short title",
      "explanation": "why this is a problem",
      "suggestion": "specific fix"
    }}
  ]
}}

Do not include markdown.
Do not wrap the response inside ```json.
Do not add any text before or after the JSON.

Swift code:

{swift_code}
"""

interaction = client.interactions.create(
    model="gemini-3.5-flash-lite",
    input=prompt
)

raw_response = interaction.output_text

print("RAW RESPONSE:")
print(raw_response)

review = json.loads(raw_response)

print("\n==============================")
print("      iOS CODE REVIEW")
print("==============================")

print(f"\nRisk: {review['overall_risk']}")
print(f"Recommendation: {review['recommendation']}")

print("\nSummary:")
print(review["summary"])

print("\nFindings:")

for index, finding in enumerate(review["findings"], start=1):
    print(
        f"\n{index}. "
        f"[{finding['severity']}] "
        f"{finding['category']}"
    )

    print(f"   {finding['title']}")
    print(f"   {finding['explanation']}")
    print(f"   Suggestion: {finding['suggestion']}")