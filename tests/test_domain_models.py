from datetime import datetime
import pytest
from pydantic import ValidationError
from reforge.domain.models import (
    ExcavationState,
    ExcavationStatus,
    HeritageReport,
    PreservationCategory,
    PreservationProfile,
    RepositoryProfile,
)

def test_repository_profile_valid():
    """Test that a valid RepositoryProfile parses correctly."""
    now = datetime.utcnow()
    profile = RepositoryProfile(
        url="https://github.com/example/repo",
        name="repo",
        owner="example",
        primary_language="Python",
        languages={"Python": 1.0},
        stars=10,
        forks=2,
        watchers=5,
        license="MIT",
        contributors_count=3,
        last_commit_at=now,
        created_at=now,
        readme_content="README",
    )
    assert profile.name == "repo"
    assert profile.stars == 10
    assert profile.languages["Python"] == 1.0


def test_repository_profile_invalid_stars():
    """Test that negative stars raise a validation error."""
    now = datetime.utcnow()
    with pytest.raises(ValidationError):
        RepositoryProfile(
            url="https://github.com/example/repo",
            name="repo",
            owner="example",
            primary_language="Python",
            languages={},
            stars=-5,  # Invalid
            forks=0,
            watchers=0,
            last_commit_at=now,
            created_at=now,
        )


def test_preservation_category_invalid_score():
    """Test that score must be between 0 and 100."""
    with pytest.raises(ValidationError):
        PreservationCategory(score=105, explanation="Too high")  # Invalid

    with pytest.raises(ValidationError):
        PreservationCategory(score=-1, explanation="Too low")  # Invalid

    category = PreservationCategory(score=85, explanation="Great")
    assert category.score == 85


def test_excavation_state_defaults():
    """Test that default values are set correctly on ExcavationState."""
    state = ExcavationState(
        project_id="proj-123",
        repository_url="https://github.com/example/repo",
    )
    assert state.status == ExcavationStatus.PENDING
    assert state.profile is None
    assert state.heritage_report is None
    assert len(state.audit_logs) == 0
    assert isinstance(state.created_at, datetime)
