import pytest
import os
import shutil
from datetime import datetime, timedelta
from typer.testing import CliRunner
from reforge.infrastructure.cli.main import app
from reforge.domain.models import ExcavationState, ExcavationStatus, HeritageReport, ValidationReport, SoftwareOverview, ArchitectureReport, RestorationPlan, PreservationProfile, PreservationCategory
from reforge.adapters.repositories import JSONFileProjectRepository

runner = CliRunner()

@pytest.fixture
def temp_storage_dir(tmp_path):
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return str(storage_dir)

def test_cli_history_missing(temp_storage_dir):
    result = runner.invoke(app, ["history", "non-existent-proj", "--storage-dir", temp_storage_dir])
    assert result.exit_code != 0
    assert "No excavation history found for project ID 'non-existent-proj'" in result.stdout

def test_cli_history_and_diff_success(temp_storage_dir):
    repo = JSONFileProjectRepository(storage_dir=temp_storage_dir)
    
    # Create Preservation Profile
    cat = PreservationCategory(score=50, explanation="Standard value.")
    profile = PreservationProfile(
        historical_value=cat,
        community_value=cat,
        activity_sustainability=cat,
        restoration_feasibility=cat,
        educational_value=cat,
        innovation_evolution_potential=cat
    )

    # Create two states
    t1 = datetime(2026, 7, 2, 12, 0, 0)
    state1 = ExcavationState(
        project_id="test-diff-proj",
        repository_url="https://github.com/pallets/click",
        status=ExcavationStatus.PENDING,
        updated_at=t1,
        heritage_report=HeritageReport(
            repository_url="https://github.com/pallets/click",
            overall_score=70,
            worth_preserving=True,
            explanation="Good software.",
            profile=profile,
            guiding_question_answer="Click is historic."
        ),
        software_overview=SoftwareOverview(
            languages=["python"],
            architecture_paradigm="Command-Line Interface Utility",
            explanation="CLI tool."
        ),
        architecture_report=ArchitectureReport(
            modules=["click/core.py"],
            dependencies={"click/core.py": []},
            components=["click"],
            relationships=[],
            explanation="Initial."
        ),
        restoration_plan=RestorationPlan(
            issues=[],
            steps=[],
            estimated_effort_hours=1.0,
            explanation="Easy."
        ),
        validation_report=ValidationReport(
            overall_status="PASSED",
            files_compiled=10,
            pytest_discovered=True,
            tests_passed=100,
            tests_failed=0,
            syntax_status="PASSED",
            imports_status="PASSED",
            tests_status="PASSED",
            build_status="PASSED",
            lint_status="PASSED",
            explanation="Passed."
        )
    )

    t2 = datetime(2026, 7, 2, 12, 5, 0)
    state2 = ExcavationState(
        project_id="test-diff-proj",
        repository_url="https://github.com/pallets/click",
        status=ExcavationStatus.COMPLETED,
        updated_at=t2,
        heritage_report=HeritageReport(
            repository_url="https://github.com/pallets/click",
            overall_score=75,
            worth_preserving=True,
            explanation="Great software.",
            profile=profile,
            guiding_question_answer="Click is historic."
        ),
        software_overview=SoftwareOverview(
            languages=["python"],
            architecture_paradigm="Command-Line Interface Utility",
            explanation="CLI tool."
        ),
        architecture_report=ArchitectureReport(
            modules=["click/core.py", "click/parser.py"],
            dependencies={"click/core.py": [], "click/parser.py": []},
            components=["click", "parser"],
            relationships=["parser -> click"],
            explanation="Evolved."
        ),
        restoration_plan=RestorationPlan(
            issues=[],
            steps=[],
            estimated_effort_hours=0.5,
            explanation="Easy."
        ),
        validation_report=ValidationReport(
            overall_status="PASSED",
            files_compiled=11,
            pytest_discovered=True,
            tests_passed=110,
            tests_failed=0,
            syntax_status="PASSED",
            imports_status="PASSED",
            tests_status="PASSED",
            build_status="PASSED",
            lint_status="PASSED",
            explanation="Passed."
        )
    )

    import asyncio
    asyncio.run(repo.save(state1))
    asyncio.run(repo.save(state2))

    # Test history
    history_result = runner.invoke(app, ["history", "test-diff-proj", "--storage-dir", temp_storage_dir])
    assert history_result.exit_code == 0
    assert "Excavation History for project: test-diff-proj" in history_result.stdout
    assert "70/100" in history_result.stdout
    assert "75/100" in history_result.stdout

    # Test diff (comparing t1 and t2)
    diff_result = runner.invoke(app, ["diff", "test-diff-proj", "--storage-dir", temp_storage_dir])
    assert diff_result.exit_code == 0
    assert "Comparing Excavation Runs for project: test-diff-proj" in diff_result.stdout
    assert "Heritage Score Trend: 70 -> 75 (+5)" in diff_result.stdout
    assert "Added layers: parser" in diff_result.stdout
    assert "Added dependency boundaries:" in diff_result.stdout
    assert "parser -> click" in diff_result.stdout
    assert "Test Execution Trend: 100 -> 110 passed tests (+10)" in diff_result.stdout


def test_cli_benchmark_local(temp_storage_dir):
    # Benchmark runs a quick mockup/real excavation.
    # To keep the test fast and offline-stable, we run it on local paths.
    benchmark_result = runner.invoke(app, ["benchmark", "--storage-dir", temp_storage_dir])
    
    assert benchmark_result.exit_code in (0, 1)
    assert "ReForge Archaeological Benchmark Harness" in benchmark_result.stdout
    assert "reforge-local" in benchmark_result.stdout
