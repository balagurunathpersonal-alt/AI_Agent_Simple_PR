import os
import re
from pathlib import Path

import requests


GITHUB_API_URL = "https://api.github.com"


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

    # Cross-platform
    ".dart",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",

    # Backend
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

    # Configuration
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


class GitHubPRDebugClient:

    def __init__(
        self,
        owner: str,
        repo: str,
        pull_request_number: int,
    ):
        self.owner = owner
        self.repo = repo
        self.pull_request_number = pull_request_number

        self.token = os.environ["GITHUB_TOKEN"]

    # ========================================================
    # HTTP Helpers
    # ========================================================

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        }

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
        """
        Returns metadata for the configured pull request.
        """

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

        result = {
            "number": data["number"],
            "title": data["title"],
            "description": (
                data.get("body") or ""
            ),
            "state": data["state"],
            "author": data["user"]["login"],
            "source_branch": data["head"]["ref"],
            "source_sha": data["head"]["sha"],
            "target_branch": data["base"]["ref"],
            "commits": data["commits"],
            "changed_files": data["changed_files"],
            "additions": data["additions"],
            "deletions": data["deletions"],
        }

        print("\n📋 PR INFORMATION")
        print("=" * 70)
        print(f"PR Number      : {result['number']}")
        print(f"Title          : {result['title']}")
        print(f"Author         : {result['author']}")
        print(f"Source Branch  : {result['source_branch']}")
        print(f"Source SHA     : {result['source_sha']}")
        print(f"Target Branch  : {result['target_branch']}")
        print(f"Changed Files  : {result['changed_files']}")
        print(f"Additions      : {result['additions']}")
        print(f"Deletions      : {result['deletions']}")
        print("=" * 70)

        return result

    # ========================================================
    # Changed Files
    # ========================================================

    def get_pull_request_files(
        self
    ) -> list[dict]:
        """
        Returns metadata for reviewable files in the PR.

        Does not return the full diff.
        The AI should call get_file_diff() separately.
        """

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

        for file_data in all_files:

            filename = file_data["filename"]

            if not self._is_supported_file(
                filename
            ):
                continue

            reviewable_files.append(
                {
                    "filename": filename,
                    "status": file_data["status"],
                    "additions": file_data["additions"],
                    "deletions": file_data["deletions"],
                    "changes": file_data["changes"],
                }
            )

        print("\n📁 FILES CHANGED")
        print("=" * 70)

        for file_data in reviewable_files:
            print(
                f"- {file_data['filename']} "
                f"({file_data['status']}, "
                f"+{file_data['additions']} "
                f"-{file_data['deletions']})"
            )

        print("=" * 70)

        return reviewable_files

    # ========================================================
    # Exact Diff
    # ========================================================

    def get_file_diff(
        self,
        filepath: str
    ) -> str:
        """
        Returns the GitHub diff patch for one changed file.

        Args:
            filepath:
                Repository-relative path.
        """

        print(
            "\n🔧 TOOL CALLED: "
            f"get_file_diff({filepath})"
        )

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/"
            f"{self.repo}/pulls/"
            f"{self.pull_request_number}/files"
        )

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
                return (
                    f"GitHub error "
                    f"{response.status_code}: "
                    f"{response.text}"
                )

            files = response.json()

            if not files:
                break

            for file_data in files:

                if (
                    file_data["filename"]
                    == filepath
                ):

                    patch = file_data.get(
                        "patch",
                        ""
                    )

                    print()
                    print("=" * 70)
                    print(
                        f"DIFF RECEIVED BY AGENT: "
                        f"{filepath}"
                    )
                    print("=" * 70)

                    if patch:
                        print(patch)
                    else:
                        print(
                            "[No textual patch "
                            "returned by GitHub]"
                        )

                    print("=" * 70)

                    return patch

            if len(files) < 100:
                break

            page += 1

        return (
            f"No diff found for {filepath}"
        )

    # ========================================================
    # Read Full File
    # ========================================================

    def read_repository_file(
        self,
        filepath: str
    ) -> str:
        """
        Reads the complete file from the PR head commit.
        """

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

        source_sha = pr["source_sha"]

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
                f"Unable to read {filepath}. "
                f"GitHub returned "
                f"{response.status_code}."
            )

        data = response.json()

        download_url = data.get(
            "download_url"
        )

        if not download_url:
            return (
                f"No downloadable content "
                f"for {filepath}"
            )

        file_response = requests.get(
            download_url,
            headers=self._headers(),
            timeout=30,
        )

        if file_response.status_code != 200:
            return (
                f"Unable to download "
                f"{filepath}"
            )

        print(
            f"📖 Full file loaded: "
            f"{filepath}"
        )

        return file_response.text

    # ========================================================
    # Valid Inline Diff Lines
    # ========================================================

    def get_valid_diff_lines(
        self,
        filepath: str
    ) -> set[int]:

        patch = self.get_file_diff(
            filepath
        )

        if not patch:
            return set()

        valid_lines = set()

        new_line_number = None

        for diff_line in patch.splitlines():

            if diff_line.startswith("@@"):

                match = re.search(
                    r"\+(\d+)",
                    diff_line
                )

                if match:
                    new_line_number = int(
                        match.group(1)
                    )

                continue

            if new_line_number is None:
                continue

            # Removed lines exist on LEFT only.
            if (
                diff_line.startswith("-")
                and not diff_line.startswith(
                    "---"
                )
            ):
                continue

            # Added line.
            if (
                diff_line.startswith("+")
                and not diff_line.startswith(
                    "+++"
                )
            ):

                valid_lines.add(
                    new_line_number
                )

                new_line_number += 1

                continue

            # Context line.
            if not diff_line.startswith("\\"):

                valid_lines.add(
                    new_line_number
                )

                new_line_number += 1

        return valid_lines

    # ========================================================
    # General PR Comment
    # ========================================================

    def post_pull_request_comment(
        self,
        comment_body: str
    ) -> bool:

        print(
            "\n🚀 ACTION: "
            "post_pull_request_comment()"
        )

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
                "✅ Summary comment posted."
            )

            return True

        print(
            "\n❌ Failed to post "
            "summary comment."
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
    # Inline Review Comment
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
            f"{filepath}:{line_number})"
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
                f"⚠️ Line {line_number} "
                f"is not part of the "
                f"RIGHT-side PR diff."
            )

            return False

        pr = self.get_pull_request()

        if "error" in pr:
            return False

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/"
            f"{self.repo}/pulls/"
            f"{self.pull_request_number}/"
            f"comments"
        )

        payload = {
            "body": comment_body,
            "commit_id": pr["source_sha"],
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
                "✅ Inline comment posted."
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