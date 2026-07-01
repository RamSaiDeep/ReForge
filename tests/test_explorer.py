import pytest
from unittest.mock import AsyncMock
from reforge.domain.interfaces import GitCloner, WorkspaceInspector
from reforge.domain.models import ExcavationState, ExcavationStatus, SoftwareOverview
from reforge.usecases.explorer import ExplorerAgent

@pytest.fixture
def mock_cloner() -> AsyncMock:
    return AsyncMock(spec=GitCloner)


@pytest.fixture
def mock_inspector() -> AsyncMock:
    return AsyncMock(spec=WorkspaceInspector)


@pytest.fixture
def base_state() -> ExcavationState:
    return ExcavationState(
        project_id="proj-333",
        repository_url="https://github.com/test-owner/test-project",
        status=ExcavationStatus.EVALUATED,
    )


@pytest.mark.asyncio
async def test_explorer_agent_success(mock_cloner, mock_inspector, base_state):
    mock_overview = SoftwareOverview(
        entry_points=["main.py"],
        dependencies=["fastapi"],
        frameworks=["FastAPI"],
        build_system="pip",
        directory_tree={"/": ["main.py", "requirements.txt"]},
        documentation_files=["README.md"],
        explanation="Everything checks out.",
    )
    mock_inspector.inspect.return_value = mock_overview

    agent = ExplorerAgent(cloner=mock_cloner, inspector=mock_inspector, storage_base_dir=".test_workspaces")
    overview = await agent.run(base_state)

    # Assertions
    assert overview == mock_overview
    assert base_state.status == ExcavationStatus.UNDERSTOOD
    assert base_state.software_overview == mock_overview
    assert base_state.local_path is not None
    assert ".test_workspaces" in base_state.local_path
    
    mock_cloner.clone.assert_called_once_with(
        "https://github.com/test-owner/test-project", base_state.local_path
    )
    mock_inspector.inspect.assert_called_once_with(base_state.local_path)
    
    assert len(base_state.audit_logs) == 1
    log = base_state.audit_logs[0]
    assert log.agent_name == "Repository Explorer"
    assert log.action_type == "WORKSPACE_UNDERSTANDING"


@pytest.mark.asyncio
async def test_explorer_agent_failure(mock_cloner, mock_inspector, base_state):
    mock_cloner.clone.side_effect = RuntimeError("Cloning unauthorized")

    agent = ExplorerAgent(cloner=mock_cloner, inspector=mock_inspector, storage_base_dir=".test_workspaces")
    
    with pytest.raises(RuntimeError, match="Cloning unauthorized"):
        await agent.run(base_state)

    # Assertions
    assert base_state.status == ExcavationStatus.FAILED
    assert base_state.software_overview is None
    
    assert len(base_state.audit_logs) == 1
    log = base_state.audit_logs[0]
    assert log.agent_name == "Repository Explorer"
    assert log.action_type == "WORKSPACE_UNDERSTANDING_FAILED"
    assert "Cloning unauthorized" in log.explanation
