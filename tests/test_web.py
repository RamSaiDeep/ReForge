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
from reforge.infrastructure.web import app, get_repository, get_supervisor

# Setup test overrides
test_repository = InMemoryProjectRepository()
test_scout = AsyncMock(spec=ScoutAgent)
test_heritage = AsyncMock(spec=HeritageEvaluator)
test_explorer = AsyncMock(spec=ExplorerAgent)
test_architect = AsyncMock(spec=ArchitectAgent)

test_supervisor = SupervisorWorkflow(
    repository=test_repository,
    scout_agent=test_scout,
    heritage_evaluator=test_heritage,
    explorer_agent=test_explorer,
    architect_agent=test_architect
)

app.dependency_overrides[get_repository] = lambda: test_repository
app.dependency_overrides[get_supervisor] = lambda: test_supervisor

client = TestClient(app)

@pytest.fixture(autouse=True)
async def clear_repository():
    # Empty repository before each test run
    test_repository._projects.clear()


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
    test_scout.run.side_effect = scout_side

    mock_report = MagicMock(spec=HeritageReport)
    mock_report.worth_preserving = True
    async def heritage_side(state):
        state.heritage_report = mock_report
        state.status = ExcavationStatus.EVALUATED
        return mock_report
    test_heritage.run.side_effect = heritage_side

    async def explorer_side(state):
        state.local_path = "/tmp/mock-repo-path"
        state.status = ExcavationStatus.UNDERSTOOD
        return MagicMock()
    test_explorer.run.side_effect = explorer_side

    async def architect_side(state):
        state.status = ExcavationStatus.RECONSTRUCTED
        return MagicMock()
    test_architect.run.side_effect = architect_side

    # Excavate
    response = client.post("/projects/exc-proj/excavate")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["status"] == "RECONSTRUCTED"
    assert data["profile"]["name"] == "exc"

