import os
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

    # Config / data
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
        self.pull_request_number = pull_request_number

        self.token = os.environ["GITHUB_TOKEN"]

    # ========================================================
    # HTTP helpers
    # ========================================================

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
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

        return ".." not in Path(filepath).parts

    # ========================================================
    # PR details
    # ========================================================

    def get_pull_request(self) -> dict:
        """
        Returns metadata about the configured pull request.
        """

        print(
            "\n🔧 TOOL CALLED: "
            "get_pull_request()"
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
            "description": (
                data.get("body") or ""
            ),
            "state": data["state"],
            "author": (
                data["user"]["login"]
            ),
            "source_branch": (
                data["head"]["ref"]
            ),
            "source_sha": (
                data["head"]["sha"]
            ),
            "target_branch": (
                data["base"]["ref"]
            ),
            "commits": data["commits"],
            "changed_files": (
                data["changed_files"]
            ),
            "additions": data["additions"],
            "deletions": data["deletions"],
        }

    # ========================================================
    # Changed files
    # ========================================================

    def get_pull_request_files(
        self
    ) -> list[dict]:
        """
        Returns files changed by the pull request.
        """

        print(
            "\n🔧 TOOL CALLED: "
            "get_pull_request_files()"
        )

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/{self.repo}/pulls/"
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

            page_files = response.json()

            if not page_files:
                break

            all_files.extend(page_files)

            if len(page_files) < 100:
                break

            page += 1

        reviewable_files = []

        for file in all_files:

            filename = file["filename"]

            if not self._is_supported_file(
                filename
            ):
                continue

            reviewable_files.append(
                {
                    "filename": filename,
                    "status": (
                        file["status"]
                    ),
                    "additions": (
                        file["additions"]
                    ),
                    "deletions": (
                        file["deletions"]
                    ),
                    "changes": (
                        file["changes"]
                    ),
                    "patch": (
                        file.get(
                            "patch",
                            ""
                        )
                    ),
                }
            )

        print(
            "\n📁 Reviewable files:",
            len(reviewable_files)
        )

        return reviewable_files

    # ========================================================
    # Read repository file
    # ========================================================

    def read_repository_file(
        self,
        filepath: str
    ) -> str:
        """
        Reads a file from the PR source commit.
        """

        print(
            "\n🔧 TOOL CALLED: "
            f"read_repository_file({filepath})"
        )

        if not self._safe_path(filepath):
            return (
                "Access denied: "
                "invalid file path"
            )

        pr = self.get_pull_request()

        if "error" in pr:
            return pr["error"]

        source_sha = pr["source_sha"]

        url = (
            f"{GITHUB_API_URL}/repos/"
            f"{self.owner}/{self.repo}/contents/"
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
                f"GitHub returned "
                f"{response.status_code}."
            )

        data = response.json()

        download_url = (
            data.get("download_url")
        )

        if not download_url:
            return (
                f"No downloadable content "
                f"found for {filepath}"
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
    # Post PR comment
    # ========================================================

    def post_pull_request_comment(
        self,
        comment_body: str
    ) -> bool:
        """
        Posts a normal PR conversation comment.

        Call this only after human approval.
        """

        print(
            "\n🚀 ACTION: "
            "post_pull_request_comment()"
        )

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

        if response.status_code == 201:
            print(
                "\n✅ Review posted "
                "successfully."
            )

            return True

        print(
            "\n❌ Failed to post review."
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