import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from reforge.adapters.github_provider import GitHubProvider

def test_github_provider_url_parsing():
    provider = GitHubProvider()
    
    # Valid formats
    assert provider._parse_url("https://github.com/owner/repo") == ("owner", "repo")
    assert provider._parse_url("http://github.com/owner/repo.git") == ("owner", "repo")
    assert provider._parse_url("www.github.com/owner/repo/") == ("owner", "repo")
    assert provider._parse_url("github.com/owner/repo") == ("owner", "repo")

    # Invalid formats
    with pytest.raises(ValueError):
        provider._parse_url("https://gitlab.com/owner/repo")
        
    with pytest.raises(ValueError):
        provider._parse_url("https://github.com/onlyowner")


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_github_provider_fetch_profile_success(mock_get):
    provider = GitHubProvider(api_token="dummy-token")

    # Setup mock responses for the three serial HTTP requests
    mock_repo_res = MagicMock()
    mock_repo_res.status_code = 200
    mock_repo_res.json.return_value = {
        "name": "my-archaeology-project",
        "owner": {"login": "archaeologist"},
        "language": "Go",
        "stargazers_count": 150,
        "forks_count": 25,
        "subscribers_count": 5,
        "license": {"spdx_id": "GPL-3.0"},
        "created_at": "2020-01-01T12:00:00Z",
        "pushed_at": "2023-06-30T18:00:00Z"
    }

    mock_lang_res = MagicMock()
    mock_lang_res.status_code = 200
    mock_lang_res.json.return_value = {"Go": 8000, "C": 2000}

    mock_readme_res = MagicMock()
    mock_readme_res.status_code = 200
    mock_readme_res.text = "# My Project\nArchaeology text."

    mock_contrib_res = MagicMock()
    mock_contrib_res.status_code = 200
    mock_contrib_res.headers = {"Link": '<https://api.github.com/...page=12>; rel="last"'}
    mock_contrib_res.json.return_value = []

    mock_releases_res = MagicMock()
    mock_releases_res.status_code = 200
    mock_releases_res.headers = {"Link": '<https://api.github.com/...page=3>; rel="last"'}
    mock_releases_res.json.return_value = []

    mock_tags_res = MagicMock()
    mock_tags_res.status_code = 200
    mock_tags_res.headers = {"Link": '<https://api.github.com/...page=5>; rel="last"'}
    mock_tags_res.json.return_value = []

    mock_commits_res = MagicMock()
    mock_commits_res.status_code = 200
    mock_commits_res.headers = {"Link": '<https://api.github.com/...page=120>; rel="last"'}
    mock_commits_res.json.return_value = []

    mock_ci_res = MagicMock()
    mock_ci_res.status_code = 200
    mock_ci_res.json.return_value = []

    # Assign side effects sequentially to mock HTTP calls
    mock_get.side_effect = [
        mock_repo_res,       # Details
        mock_lang_res,       # Languages
        mock_readme_res,     # Readme
        mock_contrib_res,    # Contributors
        mock_releases_res,   # Releases
        mock_tags_res,       # Tags
        mock_commits_res,    # Commits
        mock_ci_res          # CI Detection
    ]

    profile = await provider.fetch_profile("https://github.com/archaeologist/my-archaeology-project")

    # Assertions
    assert profile.name == "my-archaeology-project"
    assert profile.owner == "archaeologist"
    assert profile.primary_language == "Go"
    assert profile.languages == {"Go": 0.8, "C": 0.2}
    assert profile.stars == 150
    assert profile.forks == 25
    assert profile.watchers == 5
    assert profile.license == "GPL-3.0"
    assert profile.contributors_count == 12
    assert profile.readme_content == "# My Project\nArchaeology text."
    assert profile.releases_count == 3
    assert profile.tags_count == 5
    assert profile.total_commits_count == 120
    assert profile.ci_system_detected == "GitHub Actions"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_github_provider_fetch_profile_not_found(mock_get):
    provider = GitHubProvider()

    mock_res = MagicMock()
    mock_res.status_code = 404
    mock_get.return_value = mock_res

    with pytest.raises(ValueError, match="Repository not found or access denied"):
        await provider.fetch_profile("https://github.com/missing/missing-project")
