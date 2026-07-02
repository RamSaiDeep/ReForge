import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from reforge.domain.interfaces import RestorationExecutor
from reforge.domain.models import ExcavationState, ExcavationStatus, RestorationIssue, RestorationPlan
from reforge.usecases.restorer import RestorerAgent
from reforge.adapters.restoration_executor import LocalRestorationExecutor

@pytest.fixture
def mock_executor() -> AsyncMock:
    return AsyncMock(spec=RestorationExecutor)


@pytest.fixture
def base_state() -> ExcavationState:
    plan = RestorationPlan(
        issues=[],
        steps=["Create README.md"],
        estimated_effort_hours=0.5,
        explanation="Simple plan."
    )
    return ExcavationState(
        project_id="proj-restorer",
        repository_url="https://github.com/test-owner/test-project",
        status=ExcavationStatus.AWAITING_APPROVAL,
        local_path="/tmp/mock-repo-path",
        restoration_plan=plan
    )


@pytest.mark.asyncio
async def test_local_restoration_executor_execution(tmp_path):
    plan = RestorationPlan(
        issues=[],
        steps=["Create python virtual environment: python -m venv .venv", "Create requirements.txt", "Create README.md"],
        estimated_effort_hours=0.5,
        explanation="Testing."
    )

    executor = LocalRestorationExecutor()
    logs = await executor.execute(str(tmp_path), plan)

    # Assertions
    assert any("[FS] Created mock virtual environment directory" in log for log in logs)
    assert any("[FS] Created default requirements file" in log for log in logs)
    assert any("[FS] Created default documentation" in log for log in logs)
    
    assert os.path.exists(tmp_path / ".venv")
    assert os.path.exists(tmp_path / "requirements.txt")
    assert os.path.exists(tmp_path / "README.md")


@pytest.mark.asyncio
async def test_restorer_agent_success(mock_executor, base_state):
    mock_executor.execute.return_value = ["[EXEC] Complete"]
    
    agent = RestorerAgent(executor=mock_executor)
    logs = await agent.run(base_state)

    # Assertions
    assert logs == ["[EXEC] Complete"]
    assert base_state.status == ExcavationStatus.RESTORED
    
    mock_executor.execute.assert_called_once_with("/tmp/mock-repo-path", base_state.restoration_plan)
    
    assert len(base_state.audit_logs) == 1
    log = base_state.audit_logs[0]
    assert log.agent_name == "Restorer Agent"
    assert log.action_type == "RESTORATION_EXECUTION"


@pytest.mark.asyncio
async def test_restorer_agent_failure(mock_executor, base_state):
    mock_executor.execute.side_effect = RuntimeError("Shell write denied")

    agent = RestorerAgent(executor=mock_executor)
    
    with pytest.raises(RuntimeError, match="Shell write denied"):
        await agent.run(base_state)

    # Assertions
    assert base_state.status == ExcavationStatus.FAILED
    
    assert len(base_state.audit_logs) == 1
    log = base_state.audit_logs[0]
    assert log.agent_name == "Restorer Agent"
    assert log.action_type == "RESTORATION_EXECUTION_FAILED"


@pytest.mark.asyncio
async def test_restorer_agent_missing_inputs():
    agent = RestorerAgent(executor=AsyncMock())

    # missing local_path
    state1 = ExcavationState(
        project_id="p1", repository_url="https://github.com/1", status=ExcavationStatus.AWAITING_APPROVAL
    )
    with pytest.raises(ValueError, match="must contain local_path"):
        await agent.run(state1)

    # missing plan
    state2 = ExcavationState(
        project_id="p2", repository_url="https://github.com/2", status=ExcavationStatus.AWAITING_APPROVAL, local_path="/tmp"
    )
    with pytest.raises(ValueError, match="must contain an approved restoration_plan"):
        await agent.run(state2)


@pytest.mark.asyncio
async def test_local_restoration_executor_semantic_migrations(tmp_path):
    # Setup legacy python file with deprecated imp library
    legacy_py = tmp_path / "legacy.py"
    legacy_py.write_text("import imp\ndef load():\n    imp.load_source('mod', 'file.py')\n", encoding="utf-8")

    plan = RestorationPlan(
        issues=[],
        steps=[
            "Add project license file: create LICENSE",
            "Configure automated CI workflow: create .github/workflows/ci.yml",
            "Refactor deprecated Python imports: replace 'imp' usage"
        ],
        estimated_effort_hours=4.5,
        explanation="Archaeological refactoring."
    )

    executor = LocalRestorationExecutor()
    logs = await executor.execute(str(tmp_path), plan)

    # Check assertions for filesystem repairs
    assert os.path.exists(tmp_path / "LICENSE")
    assert os.path.exists(tmp_path / ".github" / "workflows" / "ci.yml")

    # Check assertion that source file was semantically refactored
    content = legacy_py.read_text(encoding="utf-8")
    assert "import importlib as imp" in content
    assert "imp.load_source" in content
    assert any("[FS] Refactored" in log for log in logs)
