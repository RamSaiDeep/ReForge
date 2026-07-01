import os
import re
from datetime import datetime
from typing import Dict, Optional
import httpx
from reforge.domain.interfaces import GitProvider
from reforge.domain.models import RepositoryProfile

class GitHubProvider(GitProvider):
    """Concrete implementation of GitProvider for the GitHub platform."""

    def __init__(self, api_token: Optional[str] = None) -> None:
        # If no token is passed, look up standard GITHUB_TOKEN environment variable
        self.api_token = api_token or os.getenv("GITHUB_TOKEN")

    def _parse_url(self, repo_url: str) -> tuple[str, str]:
        """Extract owner and repository name from a GitHub URL."""
        pattern = r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/.]+)(?:\.git)?(?:/|$)"
        match = re.search(pattern, repo_url)
        if not match:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
        return match.group(1), match.group(2)

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": "ReForge-Software-Archaeology-Agent",
            "Accept": "application/vnd.github.v3+json",
        }
        if self.api_token:
            headers["Authorization"] = f"token {self.api_token}"
        return headers

    async def fetch_profile(self, repo_url: str) -> RepositoryProfile:
        owner, repo = self._parse_url(repo_url)
        
        async with httpx.AsyncClient() as client:
            headers = self._get_headers()
            
            # 1. Fetch Repository Details
            repo_api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = await client.get(repo_api_url, headers=headers)
            
            if response.status_code == 404:
                raise ValueError(f"Repository not found or access denied: {repo_url}")
            elif response.status_code != 200:
                raise Exception(
                    f"GitHub API error ({response.status_code}) fetching repo: {response.text}"
                )
            
            repo_data = response.json()

            # 2. Fetch Repository Languages (to calculate percentages)
            lang_api_url = f"https://api.github.com/repos/{owner}/{repo}/languages"
            lang_res = await client.get(lang_api_url, headers=headers)
            languages: Dict[str, float] = {}
            if lang_res.status_code == 200:
                lang_data = lang_res.json()
                total_bytes = sum(lang_data.values())
                if total_bytes > 0:
                    languages = {lang: round(bytes_cnt / total_bytes, 4) for lang, bytes_cnt in lang_data.items()}

            # 3. Fetch README Content (using raw Accept header to avoid base64 decoding)
            readme_headers = headers.copy()
            readme_headers["Accept"] = "application/vnd.github.raw"
            readme_api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
            readme_res = await client.get(readme_api_url, headers=readme_headers)
            readme_content: Optional[str] = None
            if readme_res.status_code == 200:
                readme_content = readme_res.text

            # Clean and map GitHub date strings to datetime objects
            created_at = datetime.fromisoformat(repo_data["created_at"].replace("Z", "+00:00"))
            pushed_at = datetime.fromisoformat(repo_data["pushed_at"].replace("Z", "+00:00"))

            # Note: License can be missing or can have a 'key'/'spdx_id'
            license_name = None
            if repo_data.get("license"):
                license_name = repo_data["license"].get("spdx_id") or repo_data["license"].get("name")

            # Extract basic contributor count (simplistic fallback, using api contributors link)
            # Fetching page 1 with per_page=1 to get link headers for true count is optimal, 
            # but for metadata we can read forks/stars/contributors estimation or do a quick call.
            # Let's do a simple call or estimate. Let's make a quick head/get call with 1 per_page
            # to parse Link headers or just default to 0 and fetch async.
            contrib_count = 0
            contrib_api_url = f"https://api.github.com/repos/{owner}/{repo}/contributors?per_page=1"
            contrib_res = await client.get(contrib_api_url, headers=headers)
            if contrib_res.status_code == 200:
                # GitHub returns a Link header for pagination. E.g.:
                # <...page=42>; rel="last"
                # If present, we parse the last page number.
                link_header = contrib_res.headers.get("Link")
                if link_header:
                    match = re.search(r'page=(\d+)>; rel="last"', link_header)
                    if match:
                        contrib_count = int(match.group(1))
                    else:
                        contrib_count = len(contrib_res.json())
                else:
                    contrib_count = len(contrib_res.json())

            return RepositoryProfile(
                url=repo_url,
                name=repo_data["name"],
                owner=repo_data["owner"]["login"],
                primary_language=repo_data.get("language") or "Unknown",
                languages=languages,
                stars=repo_data.get("stargazers_count", 0),
                forks=repo_data.get("forks_count", 0),
                watchers=repo_data.get("subscribers_count") or repo_data.get("watchers_count", 0),
                license=license_name,
                contributors_count=contrib_count,
                last_commit_at=pushed_at,
                created_at=created_at,
                readme_content=readme_content
            )
