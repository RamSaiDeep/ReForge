from datetime import datetime
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from reforge.adapters.repositories import InMemoryProjectRepository
from reforge.domain.models import ExcavationState, ExcavationStatus, HeritageReport, RepositoryProfile
from reforge.usecases.scout import ScoutAgent
from reforge.usecases.heritage import HeritageEvaluator
from reforge.usecases.explorer import ExplorerAgent
from reforge.usecases.supervisor import SupervisorWorkflow
from reforge.usecases.architect import ArchitectAgent
from reforge.usecases.restoration_planner import RestorationPlannerAgent
from reforge.infrastructure.web import app, get_repository, get_supervisor

from reforge.usecases.restorer import RestorerAgent
from reforge.usecases.evolution_planner import EvolutionPlannerAgent

# Setup mocks (do not start name with 'test_' to avoid pytest collection warnings/errors)
mock_repository = InMemoryProjectRepository()
mock_scout = AsyncMock(spec=ScoutAgent)
mock_heritage = AsyncMock(spec=HeritageEvaluator)
mock_explorer = AsyncMock(spec=ExplorerAgent)
mock_architect = AsyncMock(spec=ArchitectAgent)
mock_restoration_planner = AsyncMock(spec=RestorationPlannerAgent)
mock_restorer = AsyncMock(spec=RestorerAgent)
mock_evolution_planner = AsyncMock(spec=EvolutionPlannerAgent)

mock_supervisor = SupervisorWorkflow(
    repository=mock_repository,
    scout_agent=mock_scout,
    heritage_evaluator=mock_heritage,
    explorer_agent=mock_explorer,
    architect_agent=mock_architect,
    restoration_planner=mock_restoration_planner,
    restorer_agent=mock_restorer,
    evolution_planner=mock_evolution_planner
)

app.dependency_overrides[get_repository] = lambda: mock_repository
app.dependency_overrides[get_supervisor] = lambda: mock_supervisor

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_repository():
    # Empty repository before each test run
    mock_repository._projects.clear()


def test_create_project_api():
    payload = {"project_id": "api-project", "repository_url": "https://github.com/api/test"}
    response = client.post("/projects", json=payload)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["project_id"] == "api-project"
    assert data["status"] == "PENDING"

    # Test duplicate creation failure
    response_dup = client.post("/projects", json=payload)
    assert response_dup.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response_dup.json()["detail"]


def test_get_project_api():
    # Attempt lookup for non-existent
    response_missing = client.get("/projects/missing-project")
    assert response_missing.status_code == status.HTTP_404_NOT_FOUND

    # Setup project in repo
    payload = {"project_id": "get-project", "repository_url": "https://github.com/api/test"}
    client.post("/projects", json=payload)

    # Lookup
    response_success = client.get("/projects/get-project")
    assert response_success.status_code == status.HTTP_200_OK
    assert response_success.json()["project_id"] == "get-project"


def test_list_projects_api():
    # List empty
    response_empty = client.get("/projects")
    assert response_empty.status_code == status.HTTP_200_OK
    assert len(response_empty.json()) == 0

    # Add one
    client.post("/projects", json={"project_id": "proj-1", "repository_url": "https://github.com/1"})
    
    response_list = client.get("/projects")
    assert response_list.status_code == status.HTTP_200_OK
    assert len(response_list.json()) == 1
    assert response_list.json()[0]["project_id"] == "proj-1"


def test_excavate_project_api():
    # Setup project
    client.post("/projects", json={"project_id": "exc-proj", "repository_url": "https://github.com/exc"})

    # Setup agent mock returns
    now = datetime.utcnow()
    mock_profile = RepositoryProfile(
        url="https://github.com/exc",
        name="exc",
        owner="owner",
        primary_language="Python",
        languages={},
        stars=10,
        forks=5,
        watchers=1,
        last_commit_at=now,
        created_at=now,
    )
    
    async def scout_side(state):
        state.profile = mock_profile
        state.status = ExcavationStatus.DISCOVERED
        return mock_profile
    mock_scout.run.side_effect = scout_side

    mock_report = MagicMock(spec=HeritageReport)
    mock_report.worth_preserving = True
    async def heritage_side(state):
        state.heritage_report = mock_report
        state.status = ExcavationStatus.EVALUATED
        return mock_report
    mock_heritage.run.side_effect = heritage_side

    async def explorer_side(state):
        state.local_path = "/tmp/mock-repo-path"
        state.status = ExcavationStatus.UNDERSTOOD
        return MagicMock()
    mock_explorer.run.side_effect = explorer_side

    async def architect_side(state):
        state.status = ExcavationStatus.RECONSTRUCTED
        return MagicMock()
    mock_architect.run.side_effect = architect_side

    async def restoration_side(state):
        state.status = ExcavationStatus.AWAITING_APPROVAL
        return MagicMock()
    mock_restoration_planner.run.side_effect = restoration_side

    # Excavate
    response = client.post("/projects/exc-proj/excavate")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["status"] == "AWAITING_APPROVAL"
    assert data["profile"]["name"] == "exc"


def test_approve_restoration_api():
    # Setup project
    client.post("/projects", json={"project_id": "approve-proj", "repository_url": "https://github.com/app"})

    # Setup supervisor mock behavior
    async def approve_mock(project_id):
        # Retrieve state from repo and update
        state = await mock_repository.get_by_id(project_id)
        state.status = ExcavationStatus.RESTORED
        return state
        
    mock_supervisor.approve_and_restore = approve_mock

    # Approve
    response = client.post("/projects/approve-proj/approve")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "RESTORED"
