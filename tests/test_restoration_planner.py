import pytest
import os
from reforge.domain.models import ExcavationState, ExcavationStatus, SoftwareOverview, ArchitectureReport
from reforge.usecases.restoration_planner import RestorationPlannerAgent

@pytest.fixture
def base_state() -> ExcavationState:
    return ExcavationState(
        project_id="proj-restoration",
        repository_url="https://github.com/test-owner/test-project",
        status=ExcavationStatus.RECONSTRUCTED,
    )


@pytest.mark.asyncio
async def test_restoration_planner_issues_found(base_state):
    # Setup software overview with maximum issues (none of the fields are populated)
    base_state.software_overview = SoftwareOverview(
        entry_points=[],
        dependencies=[],
        frameworks=[],
        build_system=None,
        directory_tree={},
        documentation_files=[],
        explanation="Untidy code.",
    )
    
    agent = RestorationPlannerAgent()
    plan = await agent.run(base_state)

    # Assertions
    assert base_state.status == ExcavationStatus.AWAITING_APPROVAL
    assert plan == base_state.restoration_plan
    assert len(plan.issues) == 3
    
    severities = [issue.severity for issue in plan.issues]
    assert "HIGH" in severities    # missing build system
    assert "MEDIUM" in severities  # empty dependencies
    assert "LOW" in severities     # missing docs
    
    # Effort: 6.0 (HIGH) + 3.0 (MEDIUM) + 1.5 (LOW) = 10.5 hours
    assert plan.estimated_effort_hours == 10.5
    assert len(plan.steps) >= 3

    assert len(base_state.audit_logs) == 1
    log = base_state.audit_logs[0]
    assert log.agent_name == "Restoration Planner"
    assert log.action_type == "RESTORATION_PLANNING"


@pytest.mark.asyncio
async def test_restoration_planner_clean_project(base_state):
    # Setup software overview with clean configuration (no issues)
    base_state.software_overview = SoftwareOverview(
        entry_points=["main.py"],
        dependencies=["fastapi"],
        frameworks=["FastAPI"],
        build_system="pip",
        directory_tree={
            "": ["main.py", "requirements.txt", "README.md", "LICENSE"],
            ".github/workflows": ["ci.yml"]
        },
        documentation_files=["README.md"],
        explanation="Perfect.",
    )

    agent = RestorationPlannerAgent()
    plan = await agent.run(base_state)

    # Assertions
    assert base_state.status == ExcavationStatus.AWAITING_APPROVAL
    assert len(plan.issues) == 0
    assert plan.estimated_effort_hours == 0.5 # default small effort
    assert len(plan.steps) == 3 # default pip steps

    assert len(base_state.audit_logs) == 1


@pytest.mark.asyncio
async def test_restoration_planner_missing_overview(base_state):
    # missing software_overview entirely
    agent = RestorationPlannerAgent()
    with pytest.raises(ValueError, match="must contain a software_overview"):
        await agent.run(base_state)


@pytest.mark.asyncio
async def test_restoration_planner_archaeological_issues(base_state, tmp_path):
    # Create pyproject.toml with deprecated python constraint
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('python = "^3.7"', encoding="utf-8")
    
    # Create source file using deprecated imp module
    src_dir = tmp_path / "src"
    os.makedirs(src_dir, exist_ok=True)
    app_py = src_dir / "app.py"
    app_py.write_text("import imp\ndef run():\n    pass\n", encoding="utf-8")

    base_state.local_path = str(tmp_path)
    base_state.software_overview = SoftwareOverview(
        entry_points=["src/app.py"],
        dependencies=["fastapi"],
        frameworks=["FastAPI"],
        build_system="pip",
        # Has pyproject.toml in root, but missing poetry.lock, LICENSE, CI/CD configs
        directory_tree={
            "": ["pyproject.toml", "src/app.py"]
        },
        documentation_files=["README.md"],
        explanation="Legacy codebase structure.",
    )

    agent = RestorationPlannerAgent()
    plan = await agent.run(base_state)

    # Verify that lockfile, CI, license, old python version, and deprecated library issues are found
    issue_types = [issue.issue_type for issue in plan.issues]
    assert "missing_lockfile" in issue_types
    assert "missing_ci_config" in issue_types
    assert "missing_license" in issue_types
    assert "unsupported_python_version" in issue_types
    assert "deprecated_library" in issue_types
