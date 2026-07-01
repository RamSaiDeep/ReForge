from datetime import datetime, timedelta, timezone
import pytest
from reforge.domain.models import ExcavationState, ExcavationStatus, RepositoryProfile
from reforge.usecases.heritage import HeritageEvaluator

@pytest.fixture
def base_state() -> ExcavationState:
    return ExcavationState(
        project_id="proj-777",
        repository_url="https://github.com/example/heritage-project",
        status=ExcavationStatus.DISCOVERED,
    )


@pytest.mark.asyncio
async def test_heritage_evaluator_worthy_project(base_state):
    # Set up a historic, classic, abandoned project
    created_at = datetime.now(timezone.utc) - timedelta(days=12 * 365)  # 12 years old
    last_commit = datetime.now(timezone.utc) - timedelta(days=4 * 365)   # 4 years old (abandoned)

    profile = RepositoryProfile(
        url="https://github.com/example/heritage-project",
        name="heritage-project",
        owner="example",
        primary_language="C++",
        languages={"C++": 0.9, "C": 0.1},
        stars=1200,   # High community value
        forks=350,
        watchers=80,
        license="GPL-3.0",
        contributors_count=45,
        created_at=created_at,
        last_commit_at=last_commit,
        readme_content="""
        # Heritage Project
        This is the pioneer compiler first introduced in 2014. 
        It contains classic algorithms for instruction selection.
        Built with CMakeLists.txt and Makefile.
        """,
    )
    base_state.profile = profile

    evaluator = HeritageEvaluator()
    report = await evaluator.run(base_state)

    # Assertions
    assert report.worth_preserving is True
    assert base_state.status == ExcavationStatus.EVALUATED
    
    # Check that individual categories are calculated
    assert report.profile.historical_value.score > 70  # Older than 10 years + pioneer/first
    assert report.profile.educational_value.score > 60   # compiler/algorithm
    assert report.profile.activity_sustainability.score == 20  # Abandoned over 3 years
    assert report.profile.restoration_feasibility.score > 50   # CMakeLists.txt/Makefile/GPL detected
    
    # Assert overall score is high
    assert report.overall_score > 50
    assert "This software deserves another chapter" in report.guiding_question_answer
    assert len(base_state.audit_logs) == 1
    assert base_state.audit_logs[0].action_type == "HERITAGE_EVALUATION"


@pytest.mark.asyncio
async def test_heritage_evaluator_unworthy_project(base_state):
    # Set up a new, low-value, active repository
    created_at = datetime.now(timezone.utc) - timedelta(days=20)  # 20 days old
    last_commit = datetime.now(timezone.utc) - timedelta(days=2)   # 2 days old (active)

    profile = RepositoryProfile(
        url="https://github.com/example/heritage-project",
        name="heritage-project",
        owner="example",
        primary_language="Javascript",
        languages={"Javascript": 1.0},
        stars=0,
        forks=0,
        watchers=0,
        license=None,
        contributors_count=1,
        created_at=created_at,
        last_commit_at=last_commit,
        readme_content="Just some scratch files.",
    )
    base_state.profile = profile

    evaluator = HeritageEvaluator()
    report = await evaluator.run(base_state)

    # Assertions
    assert report.worth_preserving is False
    assert base_state.status == ExcavationStatus.STOPPED
    assert report.overall_score < 50
    assert "does not meet the preservation threshold" in report.guiding_question_answer


@pytest.mark.asyncio
async def test_heritage_evaluator_missing_profile(base_state):
    # State has no profile
    evaluator = HeritageEvaluator()
    with pytest.raises(ValueError, match="must contain a RepositoryProfile"):
        await evaluator.run(base_state)
