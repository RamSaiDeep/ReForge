import os
import pytest
from unittest.mock import AsyncMock
from reforge.domain.models import ExcavationState, ExcavationStatus, ValidationReport
from reforge.adapters.code_validator import LocalCodeValidator
from reforge.usecases.validation_agent import ValidationAgent

@pytest.fixture
def base_state() -> ExcavationState:
    return ExcavationState(
        project_id="proj-validation",
        repository_url="https://github.com/test-owner/test-project",
        status=ExcavationStatus.RESTORED,
        local_path="/tmp/mock-repo-path"
    )


@pytest.mark.asyncio
async def test_local_code_validator_success(tmp_path):
    # Setup codebase with valid python file
    src_dir = tmp_path / "src"
    os.makedirs(src_dir, exist_ok=True)
    valid_py = src_dir / "app.py"
    valid_py.write_text("def run():\n    print('Hello World')\n", encoding="utf-8")

    validator = LocalCodeValidator()
    result = await validator.validate(str(tmp_path))
    assert result.overall_status == "PASSED"
    assert result.syntax_status == "PASSED"
    assert result.files_compiled == 1


@pytest.mark.asyncio
async def test_local_code_validator_syntax_error(tmp_path):
    # Setup codebase with invalid python file (syntax error)
    src_dir = tmp_path / "src"
    os.makedirs(src_dir, exist_ok=True)
    invalid_py = src_dir / "buggy.py"
    invalid_py.write_text("def run()  # Missing colon\n    print('Oops')\n", encoding="utf-8")

    validator = LocalCodeValidator()
    result = await validator.validate(str(tmp_path))
    assert result.overall_status == "FAILED"
    assert result.syntax_status == "FAILED"


@pytest.mark.asyncio
async def test_validation_agent_success(base_state):
    mock_validator = AsyncMock()
    mock_report = ValidationReport(
        overall_status="PASSED",
        files_compiled=1,
        pytest_discovered=False,
        tests_passed=0,
        tests_failed=0,
        syntax_status="PASSED",
        imports_status="PASSED",
        tests_status="SKIPPED",
        build_status="PASSED",
        lint_status="PASSED",
        explanation="Stub validation passed"
    )
    mock_validator.validate.return_value = mock_report

    agent = ValidationAgent(validator=mock_validator)
    result = await agent.run(base_state)

    assert result.overall_status == "PASSED"
    assert base_state.status == ExcavationStatus.VALIDATED
    assert len(base_state.audit_logs) == 1
    assert base_state.audit_logs[0].action_type == "VALIDATION_SUCCESS"


@pytest.mark.asyncio
async def test_validation_agent_failure(base_state):
    mock_validator = AsyncMock()
    mock_report = ValidationReport(
        overall_status="FAILED",
        files_compiled=1,
        pytest_discovered=False,
        tests_passed=0,
        tests_failed=0,
        syntax_status="FAILED",
        imports_status="PASSED",
        tests_status="SKIPPED",
        build_status="PASSED",
        lint_status="PASSED",
        explanation="Stub validation failed"
    )
    mock_validator.validate.return_value = mock_report

    agent = ValidationAgent(validator=mock_validator)
    
    with pytest.raises(ValueError, match="Validation failed"):
        await agent.run(base_state)

    assert base_state.status == ExcavationStatus.FAILED
    assert len(base_state.audit_logs) == 1
    assert base_state.audit_logs[0].action_type == "VALIDATION_FAILED"
