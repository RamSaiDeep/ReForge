import pytest
from typer.testing import CliRunner
from reforge.infrastructure.cli.main import app

runner = CliRunner()

def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ReForge Software Archaeology Platform" in result.stdout
    assert "v0.2.0" in result.stdout

def test_cli_doctor():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "ReForge CLI Doctor" in result.stdout
    assert "Python version >= 3.10" in result.stdout

def test_cli_list_empty():
    # Make sure we don't pick up actual user data directories during mock runs
    import os
    os.environ["REFORGE_STORAGE_DIR"] = ".reforge_data_test_empty"
    try:
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No projects found" in result.stdout
    finally:
        if os.path.exists(".reforge_data_test_empty"):
            import shutil
            shutil.rmtree(".reforge_data_test_empty")

def test_cli_status_not_found():
    result = runner.invoke(app, ["status", "missing-id"])
    assert result.exit_code != 0
    assert "Project with ID 'missing-id' not found in database" in result.stdout

def test_cli_report_not_found():
    result = runner.invoke(app, ["report", "missing-id"])
    assert result.exit_code != 0
    assert "Project with ID 'missing-id' not found in database" in result.stdout
