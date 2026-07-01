from datetime import datetime
import pytest
from unittest.mock import AsyncMock
from reforge.domain.interfaces import GitProvider
from reforge.domain.models import ExcavationState, ExcavationStatus, RepositoryProfile
from reforge.usecases.scout import ScoutAgent

@pytest.fixture
def mock_git_provider() -> AsyncMock:
    return AsyncMock(spec=GitProvider)


@pytest.fixture
def initial_state() -> ExcavationState:
    return ExcavationState(
        project_id="proj-999",
        repository_url="https://github.com/test-owner/test-repo",
        status=ExcavationStatus.PENDING,
    )


@pytest.mark.asyncio
async def test_scout_agent_success(mock_git_provider, initial_state):
    now = datetime.utcnow()
    mock_profile = RepositoryProfile(
        url="https://github.com/test-owner/test-repo",
        name="test-repo",
        owner="test-owner",
        primary_language="Python",
        languages={"Python": 1.0},
        stars=42,
        forks=5,
        watchers=10,
        license="MIT",
        contributors_count=2,
        last_commit_at=now,
        created_at=now,
        readme_content="Sample Readme",
    )
    mock_git_provider.fetch_profile.return_value = mock_profile

    agent = ScoutAgent(git_provider=mock_git_provider)
    profile = await agent.run(initial_state)

    # Assertions
    assert profile == mock_profile
    assert initial_state.status == ExcavationStatus.DISCOVERED
    assert initial_state.profile == mock_profile
    assert len(initial_state.audit_logs) == 1
    
    log = initial_state.audit_logs[0]
    assert log.agent_name == "Repository Scout"
    assert log.action_type == "METADATA_FETCH"
    assert "Successfully scouted repository" in log.explanation
    assert "test-repo" in log.explanation
    mock_git_provider.fetch_profile.assert_called_once_with(
        "https://github.com/test-owner/test-repo"
    )


@pytest.mark.asyncio
async def test_scout_agent_failure(mock_git_provider, initial_state):
    mock_git_provider.fetch_profile.side_effect = ValueError("Rate limit exceeded")

    agent = ScoutAgent(git_provider=mock_git_provider)
    
    with pytest.raises(ValueError, match="Rate limit exceeded"):
        await agent.run(initial_state)

    # Assertions
    assert initial_state.status == ExcavationStatus.FAILED
    assert initial_state.profile is None
    assert len(initial_state.audit_logs) == 1
    
    log = initial_state.audit_logs[0]
    assert log.agent_name == "Repository Scout"
    assert log.action_type == "METADATA_FETCH_FAILED"
    assert "Rate limit exceeded" in log.explanation
