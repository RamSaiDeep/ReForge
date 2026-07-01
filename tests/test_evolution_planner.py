import pytest
from reforge.domain.models import ExcavationState, ExcavationStatus, SoftwareOverview, EvolutionReport
from reforge.usecases.evolution_planner import EvolutionPlannerAgent

@pytest.fixture
def base_state() -> ExcavationState:
    overview = SoftwareOverview(
        languages=["python"],
        frameworks=["FastAPI"],
        dependencies=["fastapi", "pydantic"],
        has_tests=True,
        has_readme=True,
        explanation="Test overview"
    )
    return ExcavationState(
        project_id="proj-evo",
        repository_url="https://github.com/test-owner/test-project",
        status=ExcavationStatus.RESTORED,
        local_path="/tmp/mock-repo-path",
        software_overview=overview
    )


@pytest.mark.asyncio
async def test_evolution_planner_agent_with_async_framework(base_state):
    agent = EvolutionPlannerAgent()
    report = await agent.run(base_state)

    # Assertions
    assert isinstance(report, EvolutionReport)
    assert base_state.status == ExcavationStatus.COMPLETED
    assert base_state.evolution_report == report
    
    # Assert suggestions
    suggestions = report.suggestions
    assert len(suggestions) == 3
    assert any(s.title == "Integrate Modern Dependency Lock Files" for s in suggestions)
    assert any(s.title == "Configure Automated Linter and Code Quality Guards" for s in suggestions)
    assert any(s.title == "Adopt Fully Asynchronous Database Connections" for s in suggestions)
    
    # Check audit log
    assert len(base_state.audit_logs) == 1
    log = base_state.audit_logs[0]
    assert log.agent_name == "Evolution Planner"
    assert log.action_type == "EVOLUTION_PLANNING"


@pytest.mark.asyncio
async def test_evolution_planner_agent_without_async_framework(base_state):
    # No frameworks detected
    base_state.software_overview.frameworks = []
    
    agent = EvolutionPlannerAgent()
    report = await agent.run(base_state)

    suggestions = report.suggestions
    assert len(suggestions) == 3
    assert any(s.title == "Implement Clean Architecture Directory Layout" for s in suggestions)


@pytest.mark.asyncio
async def test_evolution_planner_agent_missing_overview():
    agent = EvolutionPlannerAgent()
    state = ExcavationState(
        project_id="proj-no-overview",
        repository_url="https://github.com/test-owner/test-project",
        status=ExcavationStatus.RESTORED
    )

    with pytest.raises(ValueError, match="must contain a software_overview"):
        await agent.run(state)
