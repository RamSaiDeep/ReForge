from datetime import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock
from reforge.adapters.repositories import InMemoryProjectRepository
from reforge.domain.models import ExcavationState, ExcavationStatus, HeritageReport, RepositoryProfile
from reforge.usecases.scout import ScoutAgent
from reforge.usecases.heritage import HeritageEvaluator
from reforge.usecases.supervisor import SupervisorWorkflow

@pytest.fixture
def mock_repository() -> InMemoryProjectRepository:
    return InMemoryProjectRepository()


from reforge.usecases.explorer import ExplorerAgent
from reforge.usecases.architect import ArchitectAgent
from reforge.usecases.restoration_planner import RestorationPlannerAgent
from reforge.usecases.restorer import RestorerAgent
from reforge.usecases.evolution_planner import EvolutionPlannerAgent
from reforge.usecases.validation_agent import ValidationAgent

@pytest.fixture
def mock_scout_agent() -> AsyncMock:
    agent = AsyncMock(spec=ScoutAgent)
    agent.name = "Repository Scout"
    return agent


@pytest.fixture
def mock_heritage_evaluator() -> AsyncMock:
    evaluator = AsyncMock(spec=HeritageEvaluator)
    evaluator.name = "Heritage Evaluator"
    return evaluator


@pytest.fixture
def mock_explorer_agent() -> AsyncMock:
    agent = AsyncMock(spec=ExplorerAgent)
    agent.name = "Repository Explorer"
    return agent


@pytest.fixture
def mock_architect_agent() -> AsyncMock:
    agent = AsyncMock(spec=ArchitectAgent)
    agent.name = "Software Architect"
    return agent


@pytest.fixture
def mock_restoration_planner() -> AsyncMock:
    agent = AsyncMock(spec=RestorationPlannerAgent)
    agent.name = "Restoration Planner"
    return agent


@pytest.fixture
def mock_restorer_agent() -> AsyncMock:
    agent = AsyncMock(spec=RestorerAgent)
    agent.name = "Restorer Agent"
    return agent


@pytest.fixture
def mock_evolution_planner() -> AsyncMock:
    agent = AsyncMock(spec=EvolutionPlannerAgent)
    agent.name = "Evolution Planner"
    return agent


@pytest.fixture
def mock_validation_agent() -> AsyncMock:
    agent = AsyncMock(spec=ValidationAgent)
    agent.name = "Validation Agent"
    return agent


@pytest.fixture
def supervisor(
    mock_repository,
    mock_scout_agent,
    mock_heritage_evaluator,
    mock_explorer_agent,
    mock_architect_agent,
    mock_restoration_planner,
    mock_restorer_agent,
    mock_evolution_planner,
    mock_validation_agent
) -> SupervisorWorkflow:
    return SupervisorWorkflow(
        repository=mock_repository,
        scout_agent=mock_scout_agent,
        heritage_evaluator=mock_heritage_evaluator,
        explorer_agent=mock_explorer_agent,
        architect_agent=mock_architect_agent,
        restoration_planner=mock_restoration_planner,
        restorer_agent=mock_restorer_agent,
        evolution_planner=mock_evolution_planner,
        validation_agent=mock_validation_agent
    )



@pytest.mark.asyncio
async def test_create_project_success(supervisor, mock_repository):
    state = await supervisor.create_project("project-1", "https://github.com/example/repo")
    assert state.project_id == "project-1"
    assert state.repository_url == "https://github.com/example/repo"
    assert state.status == ExcavationStatus.PENDING

    # Verify it exists in repository
    saved = await mock_repository.get_by_id("project-1")
    assert saved is not None
    assert saved.status == ExcavationStatus.PENDING


@pytest.mark.asyncio
async def test_create_project_duplicate(supervisor):
    await supervisor.create_project("project-1", "https://github.com/example/repo")
    with pytest.raises(ValueError, match="already exists"):
        await supervisor.create_project("project-1", "https://github.com/example/other")


@pytest.mark.asyncio
async def test_execute_excavation_worthy(supervisor, mock_repository, mock_scout_agent, mock_heritage_evaluator):
    # Create project
    await supervisor.create_project("proj-worthy", "https://github.com/example/worthy")

    # Mock ScoutAgent behavior
    now = datetime.utcnow()
    mock_profile = RepositoryProfile(
        url="https://github.com/example/worthy",
        name="worthy",
        owner="example",
        primary_language="Python",
        languages={"Python": 1.0},
        stars=500,
        forks=50,
        watchers=10,
        contributors_count=5,
        last_commit_at=now,
        created_at=now,
        readme_content="Readme content"
    )
    
    async def scout_side_effect(state: ExcavationState):
        state.profile = mock_profile
        state.status = ExcavationStatus.DISCOVERED
        return mock_profile
    mock_scout_agent.run.side_effect = scout_side_effect

    # Mock HeritageEvaluator behavior
    mock_report = MagicMock(spec=HeritageReport)
    mock_report.worth_preserving = True
    
    async def heritage_side_effect(state: ExcavationState):
        state.heritage_report = mock_report
        state.status = ExcavationStatus.EVALUATED
        return mock_report
    mock_heritage_evaluator.run.side_effect = heritage_side_effect

    # Run
    final_state = await supervisor.execute_excavation("proj-worthy")

    # Verify calls & final state
    mock_scout_agent.run.assert_called_once()
    mock_heritage_evaluator.run.assert_called_once()
    
    assert final_state.status == ExcavationStatus.EVALUATED
    assert final_state.profile == mock_profile
    assert final_state.heritage_report == mock_report

    # Verify it is saved in repo
    saved_state = await mock_repository.get_by_id("proj-worthy")
    assert saved_state.status == ExcavationStatus.EVALUATED


@pytest.mark.asyncio
async def test_execute_excavation_unworthy(supervisor, mock_repository, mock_scout_agent, mock_heritage_evaluator):
    # Create project
    await supervisor.create_project("proj-unworthy", "https://github.com/example/unworthy")

    # Mock ScoutAgent behavior
    mock_profile = MagicMock(spec=RepositoryProfile)
    async def scout_side_effect(state: ExcavationState):
        state.profile = mock_profile
        state.status = ExcavationStatus.DISCOVERED
        return mock_profile
    mock_scout_agent.run.side_effect = scout_side_effect

    # Mock HeritageEvaluator behavior
    mock_report = MagicMock(spec=HeritageReport)
    mock_report.worth_preserving = False
    
    async def heritage_side_effect(state: ExcavationState):
        state.heritage_report = mock_report
        state.status = ExcavationStatus.STOPPED
        return mock_report
    mock_heritage_evaluator.run.side_effect = heritage_side_effect

    # Run
    final_state = await supervisor.execute_excavation("proj-unworthy")

    # Verify calls & final state (should stop at STOPPED)
    mock_scout_agent.run.assert_called_once()
    mock_heritage_evaluator.run.assert_called_once()
    
    assert final_state.status == ExcavationStatus.STOPPED


@pytest.mark.asyncio
async def test_execute_excavation_unworthy_force_continue(supervisor, mock_repository, mock_scout_agent, mock_heritage_evaluator):
    await supervisor.create_project("proj-force", "https://github.com/example/force")

    # Scout succeeds
    mock_profile = MagicMock(spec=RepositoryProfile)
    async def scout_side_effect(state: ExcavationState):
        state.profile = mock_profile
        state.status = ExcavationStatus.DISCOVERED
        return mock_profile
    mock_scout_agent.run.side_effect = scout_side_effect

    # Heritage decides STOPPED
    mock_report = MagicMock(spec=HeritageReport)
    mock_report.worth_preserving = False
    async def heritage_side_effect(state: ExcavationState):
        state.heritage_report = mock_report
        state.status = ExcavationStatus.STOPPED
        return mock_report
    mock_heritage_evaluator.run.side_effect = heritage_side_effect

    # Run with force_continue=True
    final_state = await supervisor.execute_excavation("proj-force", force_continue=True)

    # Status should override to EVALUATED
    assert final_state.status == ExcavationStatus.EVALUATED


@pytest.mark.asyncio
async def test_execute_excavation_scout_failed(supervisor, mock_repository, mock_scout_agent):
    await supervisor.create_project("proj-failed", "https://github.com/example/fail")

    # Scout fails
    async def scout_side_effect(state: ExcavationState):
        state.status = ExcavationStatus.FAILED
        raise ValueError("Network Timeout")
    mock_scout_agent.run.side_effect = scout_side_effect

    # Execute
    final_state = await supervisor.execute_excavation("proj-failed")

    # Verify status is FAILED and saved
    assert final_state.status == ExcavationStatus.FAILED
    saved = await mock_repository.get_by_id("proj-failed")
    assert saved.status == ExcavationStatus.FAILED


@pytest.mark.asyncio
async def test_execute_excavation_full_pipeline(
    supervisor,
    mock_repository,
    mock_scout_agent,
    mock_heritage_evaluator,
    mock_explorer_agent,
    mock_architect_agent,
    mock_restoration_planner,
):
    await supervisor.create_project("proj-full", "https://github.com/example/full")

    # Scout
    mock_profile = MagicMock(spec=RepositoryProfile)
    async def scout_side_effect(state: ExcavationState):
        state.profile = mock_profile
        state.status = ExcavationStatus.DISCOVERED
        return mock_profile
    mock_scout_agent.run.side_effect = scout_side_effect

    # Heritage
    mock_report = MagicMock(spec=HeritageReport)
    mock_report.worth_preserving = True
    async def heritage_side_effect(state: ExcavationState):
        state.heritage_report = mock_report
        state.status = ExcavationStatus.EVALUATED
        return mock_report
    mock_heritage_evaluator.run.side_effect = heritage_side_effect

    # Explorer
    async def explorer_side_effect(state: ExcavationState):
        state.local_path = "/tmp/mock-repo-path"
        state.status = ExcavationStatus.UNDERSTOOD
        return MagicMock()
    mock_explorer_agent.run.side_effect = explorer_side_effect

    # Architect
    async def architect_side_effect(state: ExcavationState):
        state.status = ExcavationStatus.RECONSTRUCTED
        return MagicMock()
    mock_architect_agent.run.side_effect = architect_side_effect

    # Restoration Planner
    async def restoration_side_effect(state: ExcavationState):
        state.status = ExcavationStatus.AWAITING_APPROVAL
        return MagicMock()
    mock_restoration_planner.run.side_effect = restoration_side_effect

    # Run
    final_state = await supervisor.execute_excavation("proj-full")

    # Assert
    assert final_state.status == ExcavationStatus.AWAITING_APPROVAL
    mock_scout_agent.run.assert_called_once()
    mock_heritage_evaluator.run.assert_called_once()
    mock_explorer_agent.run.assert_called_once()
    mock_architect_agent.run.assert_called_once()
    mock_restoration_planner.run.assert_called_once()


@pytest.mark.asyncio
async def test_approve_and_restore_success(supervisor, mock_repository, mock_restorer_agent, mock_validation_agent, mock_evolution_planner):
    # Setup project in awaiting approval
    state = ExcavationState(
        project_id="app-proj",
        repository_url="https://github.com/example/app",
        status=ExcavationStatus.AWAITING_APPROVAL
    )
    await mock_repository.save(state)

    async def restorer_side(state):
        state.status = ExcavationStatus.RESTORED
        return []
    mock_restorer_agent.run.side_effect = restorer_side

    async def validation_side(state):
        state.status = ExcavationStatus.VALIDATED
        return True
    mock_validation_agent.run.side_effect = validation_side

    async def evolution_side(state):
        state.status = ExcavationStatus.COMPLETED
        return MagicMock()
    mock_evolution_planner.run.side_effect = evolution_side

    # Execute
    updated_state = await supervisor.approve_and_restore("app-proj")
    
    assert updated_state.status == ExcavationStatus.COMPLETED
    mock_restorer_agent.run.assert_called_once()
    mock_validation_agent.run.assert_called_once()
    mock_evolution_planner.run.assert_called_once()


@pytest.mark.asyncio
async def test_approve_and_restore_invalid_status(supervisor, mock_repository):
    # Project is in PENDING state
    state = ExcavationState(
        project_id="app-pending",
        repository_url="https://github.com/example/pending",
        status=ExcavationStatus.PENDING
    )
    await mock_repository.save(state)

    with pytest.raises(ValueError, match="must be in AWAITING_APPROVAL status"):
        await supervisor.approve_and_restore("app-pending")


