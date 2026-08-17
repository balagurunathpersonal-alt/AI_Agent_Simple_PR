import os
import re
from pathlib import Path

import requests


GITHUB_API_URL = "https://api.github.com"


SUPPORTED_EXTENSIONS = {
    # Apple
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

    # Cross-platform
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

    # Data / config
    ".json",
    ".yaml",
    ".yml",
    ".toml",

    # Shell
    ".sh",
    ".bash",
    ".zsh",

    # Database
    ".sql",

    # Documentation
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


class GitHubPRClient:

    def __init__(
        self,
        owner: str,
        repo: str,
        pull_request_number: int,
    ):
        self.owner = owner
        self.repo = repo
        self.pull_request_number = (
            pull_request_number
        )

        self.token = os.environ[
            "GITHUB_TOKEN"
        ]

    # ========================================================
    # HTTP
    # ========================================================

    def _headers(self) -> dict:

        return {
            "Authorization":
                f"Bearer {self.token}",

            "Accept":
                "application/vnd.github+json",

            "X-GitHub-Api-Version":
                "2026-03-10",
        }

    # ========================================================
    # File validation
    # ========================================================

    def _is_supported_file(
        self,
        filepath: str
    ) -> bool:

        path = Path(filepath)

        if path.name in SUPPORTED_FILENAMES:
            return True

        return (
            path.suffix.lower()
            in SUPPORTED_EXTENSIONS
        )

    def _safe_path(
        self,
        filepath: str
    ) -> bool:

        return (
            ".."
            not in Path(filepath).parts
        )

    # ========================================================
    # PR Metadata
    # ========================================================

    def get_pull_request(self) -> dict:

        print(
            "\n🔧 TOOL CALLED: "
            "get_pull_request()"
        )

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/"
            f"{self.repo}/pulls/"
            f"{self.pull_request_number}"
        )

        response = requests.get(
            url,
            headers=self._headers(),
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
            "description":
                data.get("body") or "",
            "state": data["state"],
            "author":
                data["user"]["login"],
            "source_branch":
                data["head"]["ref"],
            "source_sha":
                data["head"]["sha"],
            "target_branch":
                data["base"]["ref"],
            "commits":
                data["commits"],
            "changed_files":
                data["changed_files"],
            "additions":
                data["additions"],
            "deletions":
                data["deletions"],
        }

    # ========================================================
    # Changed Files
    # ========================================================

    def get_pull_request_files(
        self
    ) -> list[dict]:

        print(
            "\n🔧 TOOL CALLED: "
            "get_pull_request_files()"
        )

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/"
            f"{self.repo}/pulls/"
            f"{self.pull_request_number}/files"
        )

        all_files = []

        page = 1

        while True:

            response = requests.get(
                url,
                headers=self._headers(),
                params={
                    "per_page": 100,
                    "page": page,
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

            if not files:
                break

            all_files.extend(files)

            if len(files) < 100:
                break

            page += 1

        reviewable_files = []

        for file in all_files:

            filename = file[
                "filename"
            ]

            if not self._is_supported_file(
                filename
            ):
                continue

            reviewable_files.append(
                {
                    "filename":
                        filename,

                    "status":
                        file["status"],

                    "additions":
                        file["additions"],

                    "deletions":
                        file["deletions"],

                    "changes":
                        file["changes"],

                    "patch":
                        file.get(
                            "patch",
                            ""
                        ),
                }
            )

        print(
            f"\n📁 Reviewable files: "
            f"{len(reviewable_files)}"
        )

        return reviewable_files

    # ========================================================
    # Read File
    # ========================================================

    def read_repository_file(
        self,
        filepath: str
    ) -> str:

        print(
            "\n🔧 TOOL CALLED: "
            f"read_repository_file("
            f"{filepath})"
        )

        if not self._safe_path(
            filepath
        ):

            return (
                "Access denied: "
                "invalid file path."
            )

        pr = self.get_pull_request()

        if "error" in pr:
            return pr["error"]

        source_sha = pr[
            "source_sha"
        ]

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/"
            f"{self.repo}/contents/"
            f"{filepath}"
        )

        response = requests.get(
            url,
            headers=self._headers(),
            params={
                "ref": source_sha
            },
            timeout=30,
        )

        if response.status_code != 200:

            return (
                f"Unable to read "
                f"{filepath}. "
                f"Status: "
                f"{response.status_code}"
            )

        data = response.json()

        download_url = data.get(
            "download_url"
        )

        if not download_url:

            return (
                "No downloadable "
                "content found."
            )

        file_response = requests.get(
            download_url,
            headers=self._headers(),
            timeout=30,
        )

        if (
            file_response.status_code
            != 200
        ):

            return (
                f"Unable to download "
                f"{filepath}"
            )

        return file_response.text

    # ========================================================
    # Get Patch
    # ========================================================

    def get_file_patch(
        self,
        filepath: str
    ) -> str:

        files = (
            self.get_pull_request_files()
        )

        for file in files:

            if (
                file.get("filename")
                == filepath
            ):
                return file.get(
                    "patch",
                    ""
                )

        return ""

    # ========================================================
    # Parse valid RIGHT-side diff lines
    # ========================================================

    def get_valid_diff_lines(
        self,
        filepath: str
    ) -> set[int]:
        """
        Returns new-file line numbers that
        exist in the GitHub PR diff.

        These are valid RIGHT-side locations
        for inline comments.
        """

        patch = self.get_file_patch(
            filepath
        )

        if not patch:
            return set()

        valid_lines = set()

        new_line_number = None

        for line in patch.splitlines():

            # Example:
            #
            # @@ -10,4 +10,6 @@
            #
            if line.startswith("@@"):

                match = re.search(
                    r"\+(\d+)",
                    line
                )

                if match:

                    new_line_number = int(
                        match.group(1)
                    )

                continue

            if new_line_number is None:
                continue

            # Removed line exists only
            # on LEFT side.
            if (
                line.startswith("-")
                and not line.startswith(
                    "---"
                )
            ):
                continue

            # Addition
            if (
                line.startswith("+")
                and not line.startswith(
                    "+++"
                )
            ):

                valid_lines.add(
                    new_line_number
                )

                new_line_number += 1

                continue

            # Context line
            if not line.startswith("\\"):

                valid_lines.add(
                    new_line_number
                )

                new_line_number += 1

        return valid_lines

    # ========================================================
    # Inline PR comment
    # ========================================================

    def post_inline_review_comment(
        self,
        filepath: str,
        line_number: int,
        comment_body: str,
    ) -> bool:

        print(
            "\n🚀 ACTION: "
            "post_inline_review_comment("
            f"{filepath}:"
            f"{line_number})"
        )

        valid_lines = (
            self.get_valid_diff_lines(
                filepath
            )
        )

        if (
            line_number
            not in valid_lines
        ):

            print(
                "⚠️ Skipping inline "
                "comment."
            )

            print(
                f"Line {line_number} "
                "is not part of the "
                "PR diff."
            )

            return False

        pr = self.get_pull_request()

        if "error" in pr:

            print(
                "❌ Unable to get "
                "PR commit SHA."
            )

            return False

        commit_sha = pr[
            "source_sha"
        ]

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/"
            f"{self.repo}/pulls/"
            f"{self.pull_request_number}/"
            f"comments"
        )

        payload = {
            "body": comment_body,
            "commit_id": commit_sha,
            "path": filepath,
            "line": line_number,
            "side": "RIGHT",
        }

        response = requests.post(
            url,
            headers=self._headers(),
            json=payload,
            timeout=30,
        )

        if response.status_code == 201:

            print(
                "✅ Inline comment "
                "posted."
            )

            return True

        print(
            "\n❌ Failed to post "
            "inline comment."
        )

        print(
            f"Status: "
            f"{response.status_code}"
        )

        print(
            f"Response: "
            f"{response.text}"
        )

        return False

    # ========================================================
    # General PR comment
    # ========================================================

    def post_pull_request_comment(
        self,
        comment_body: str
    ) -> bool:

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/"
            f"{self.repo}/issues/"
            f"{self.pull_request_number}/"
            f"comments"
        )

        response = requests.post(
            url,
            headers=self._headers(),
            json={
                "body": comment_body
            },
            timeout=30,
        )

        if response.status_code == 201:

            print(
                "\n✅ Summary comment "
                "posted."
            )

            return True

        print(
            "\n❌ Failed to post "
            "summary comment."
        )

        print(
            response.text
        )

        return False