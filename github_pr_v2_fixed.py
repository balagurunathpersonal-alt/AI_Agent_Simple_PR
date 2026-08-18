import os
import re
from pathlib import Path

import requests


GITHUB_API_URL = "https://api.github.com"


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


class GitHubPRClientV2:

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
    # HTTP
    # ========================================================

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        }

    # ========================================================
    # File Helpers
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

        return ".." not in Path(filepath).parts

    # ========================================================
    # PR Metadata
    # ========================================================

    def get_pull_request(self) -> dict:

        print(
            "\n🔧 TOOL: get_pull_request()"
        )

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/{self.repo}/pulls/"
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
            "description": data.get("body") or "",
            "author": data["user"]["login"],
            "source_branch": data["head"]["ref"],
            "source_sha": data["head"]["sha"],
            "target_branch": data["base"]["ref"],
            "changed_files": data["changed_files"],
            "additions": data["additions"],
            "deletions": data["deletions"],
        }

    # ========================================================
    # Changed Files
    # ========================================================

    def get_pull_request_files(
        self
    ) -> list[dict]:

        print(
            "\n🔧 TOOL: "
            "get_pull_request_files()"
        )

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/{self.repo}/pulls/"
            f"{self.pull_request_number}/files"
        )

        reviewable_files = []

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
                print(
                    f"❌ GitHub files API error: "
                    f"{response.status_code}"
                )

                return []

            files = response.json()

            if not files:
                break

            for file_data in files:

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
                        "patch": file_data.get(
                            "patch",
                            ""
                        ),
                    }
                )

            if len(files) < 100:
                break

            page += 1

        print(
            f"\n📁 Reviewable files: "
            f"{len(reviewable_files)}"
        )

        return reviewable_files

    # ========================================================
    # File Diff
    # ========================================================

    def get_file_diff(
        self,
        filepath: str
    ) -> str:

        print(
            f"\n🔧 TOOL: "
            f"get_file_diff({filepath})"
        )

        files = (
            self.get_pull_request_files()
        )

        for file_data in files:

            if (
                file_data["filename"]
                == filepath
            ):
                return file_data.get(
                    "patch",
                    ""
                )

        return ""

    # ========================================================
    # Read Full Repository File
    # ========================================================

    def read_repository_file(
        self,
        filepath: str
    ) -> str:

        print(
            f"\n🔧 TOOL: "
            f"read_repository_file({filepath})"
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

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/{self.repo}/contents/"
            f"{filepath}"
        )

        response = requests.get(
            url,
            headers=self._headers(),
            params={
                "ref": pr["source_sha"]
            },
            timeout=30,
        )

        if response.status_code != 200:

            return (
                f"Unable to read {filepath}. "
                f"Status: "
                f"{response.status_code}"
            )

        data = response.json()

        download_url = data.get(
            "download_url"
        )

        if not download_url:
            return (
                f"No download URL "
                f"for {filepath}"
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
    # Valid Diff Lines
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

        for line in patch.splitlines():

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

            if (
                line.startswith("-")
                and not line.startswith(
                    "---"
                )
            ):
                continue

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

            if not line.startswith("\\"):

                valid_lines.add(
                    new_line_number
                )

                new_line_number += 1

        return valid_lines

    # ========================================================
    # Inline PR Review Comment
    # ========================================================

    def post_inline_review_comment(
        self,
        filepath: str,
        line_number: int,
        comment_body: str,
    ) -> bool:

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
                f"⚠️ Invalid inline line: "
                f"{filepath}:"
                f"{line_number}"
            )

            return False

        pr = self.get_pull_request()

        if "error" in pr:
            return False

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/{self.repo}/pulls/"
            f"{self.pull_request_number}/comments"
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

        if (
            response.status_code
            == 201
        ):
            print(
                f"✅ Inline comment posted: "
                f"{filepath}:"
                f"{line_number}"
            )

            return True

        print(
            f"❌ Failed inline comment: "
            f"{response.status_code}"
        )

        print(
            response.text
        )

        return False

    # ========================================================
    # PR Summary Comment
    # ========================================================

    def post_pull_request_comment(
        self,
        comment_body: str
    ) -> bool:

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/{self.repo}/issues/"
            f"{self.pull_request_number}/comments"
        )

        response = requests.post(
            url,
            headers=self._headers(),
            json={
                "body": comment_body
            },
            timeout=30,
        )

        if (
            response.status_code
            == 201
        ):

            print(
                "✅ Summary comment posted."
            )

            return True

        print(
            f"❌ Summary comment failed: "
            f"{response.status_code}"
        )

        print(
            response.text
        )

        return False