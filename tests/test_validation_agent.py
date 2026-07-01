import os
import pytest
from unittest.mock import AsyncMock
from reforge.domain.models import ExcavationState, ExcavationStatus
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
    assert result is True


@pytest.mark.asyncio
async def test_local_code_validator_syntax_error(tmp_path):
    # Setup codebase with invalid python file (syntax error)
    src_dir = tmp_path / "src"
    os.makedirs(src_dir, exist_ok=True)
    invalid_py = src_dir / "buggy.py"
    invalid_py.write_text("def run()  # Missing colon\n    print('Oops')\n", encoding="utf-8")

    validator = LocalCodeValidator()
    result = await validator.validate(str(tmp_path))
    assert result is False


@pytest.mark.asyncio
async def test_validation_agent_success(base_state):
    mock_validator = AsyncMock()
    mock_validator.validate.return_value = True

    agent = ValidationAgent(validator=mock_validator)
    result = await agent.run(base_state)

    assert result is True
    assert base_state.status == ExcavationStatus.VALIDATED
    assert len(base_state.audit_logs) == 1
    assert base_state.audit_logs[0].action_type == "VALIDATION_SUCCESS"


@pytest.mark.asyncio
async def test_validation_agent_failure(base_state):
    mock_validator = AsyncMock()
    mock_validator.validate.return_value = False

    agent = ValidationAgent(validator=mock_validator)
    
    with pytest.raises(ValueError, match="Validation failed"):
        await agent.run(base_state)

    assert base_state.status == ExcavationStatus.FAILED
    assert len(base_state.audit_logs) == 1
    assert base_state.audit_logs[0].action_type == "VALIDATION_FAILED"
