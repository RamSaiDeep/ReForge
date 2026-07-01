import pytest
from unittest.mock import AsyncMock
from reforge.domain.interfaces import CodeAnalyzer
from reforge.domain.models import ArchitectureReport, ExcavationState, ExcavationStatus
from reforge.usecases.architect import ArchitectAgent

@pytest.fixture
def mock_analyzer() -> AsyncMock:
    return AsyncMock(spec=CodeAnalyzer)


@pytest.fixture
def base_state() -> ExcavationState:
    return ExcavationState(
        project_id="proj-architect",
        repository_url="https://github.com/test-owner/test-project",
        status=ExcavationStatus.UNDERSTOOD,
        local_path="/tmp/mock-repo-path",
    )


@pytest.mark.asyncio
async def test_architect_agent_success(mock_analyzer, base_state):
    mock_report = ArchitectureReport(
        modules=["src/main.py"],
        dependencies={"src/main.py": []},
        components=["src"],
        relationships=[],
        explanation="Architecture mapped out perfectly.",
    )
    mock_analyzer.analyze.return_value = mock_report

    agent = ArchitectAgent(analyzer=mock_analyzer)
    report = await agent.run(base_state)

    # Assertions
    assert report == mock_report
    assert base_state.status == ExcavationStatus.RECONSTRUCTED
    assert base_state.architecture_report == mock_report
    
    mock_analyzer.analyze.assert_called_once_with("/tmp/mock-repo-path")
    
    assert len(base_state.audit_logs) == 1
    log = base_state.audit_logs[0]
    assert log.agent_name == "Software Architect"
    assert log.action_type == "ARCHITECTURE_RECONSTRUCTION"


@pytest.mark.asyncio
async def test_architect_agent_failure(mock_analyzer, base_state):
    mock_analyzer.analyze.side_effect = RuntimeError("AST parse error")

    agent = ArchitectAgent(analyzer=mock_analyzer)
    
    with pytest.raises(RuntimeError, match="AST parse error"):
        await agent.run(base_state)

    # Assertions
    assert base_state.status == ExcavationStatus.FAILED
    assert base_state.architecture_report is None
    
    assert len(base_state.audit_logs) == 1
    log = base_state.audit_logs[0]
    assert log.agent_name == "Software Architect"
    assert log.action_type == "ARCHITECTURE_RECONSTRUCTION_FAILED"
    assert "AST parse error" in log.explanation


@pytest.mark.asyncio
async def test_architect_agent_missing_local_path():
    state = ExcavationState(
        project_id="proj-no-path",
        repository_url="https://github.com/test-owner/test-project",
        status=ExcavationStatus.UNDERSTOOD,
    )
    agent = ArchitectAgent(analyzer=AsyncMock())
    with pytest.raises(ValueError, match="must contain a local_path"):
        await agent.run(state)
