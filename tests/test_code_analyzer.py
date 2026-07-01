import os
import pytest
from reforge.adapters.code_analyzer import LocalCodeAnalyzer

@pytest.mark.asyncio
async def test_local_code_analyzer(tmp_path):
    # Construct mock codebase structure inside tmp_path
    
    # 1. Domain - models.py
    domain_dir = tmp_path / "src" / "reforge" / "domain"
    os.makedirs(domain_dir, exist_ok=True)
    models_py = domain_dir / "models.py"
    models_py.write_text("class ExcavationState: pass\n", encoding="utf-8")

    # 2. Domain - interfaces.py (imports models.py)
    interfaces_py = domain_dir / "interfaces.py"
    interfaces_py.write_text(
        "from reforge.domain.models import ExcavationState\n"
        "class ProjectRepository: pass\n",
        encoding="utf-8"
    )

    # 3. Usecases - scout.py (imports models & interfaces)
    usecases_dir = tmp_path / "src" / "reforge" / "usecases"
    os.makedirs(usecases_dir, exist_ok=True)
    scout_py = usecases_dir / "scout.py"
    scout_py.write_text(
        "from reforge.domain.models import ExcavationState\n"
        "from reforge.domain.interfaces import ProjectRepository\n",
        encoding="utf-8"
    )

    # 4. Adapters - repositories.py (imports interfaces & models)
    adapters_dir = tmp_path / "src" / "reforge" / "adapters"
    os.makedirs(adapters_dir, exist_ok=True)
    repos_py = adapters_dir / "repositories.py"
    repos_py.write_text(
        "from reforge.domain.interfaces import ProjectRepository\n"
        "from reforge.domain.models import ExcavationState\n",
        encoding="utf-8"
    )

    # Run analysis
    analyzer = LocalCodeAnalyzer()
    report = await analyzer.analyze(str(tmp_path))

    # Assertions
    assert len(report.modules) == 4
    
    # Normalize paths for platform independence
    modules_norm = [m.replace("\\", "/") for m in report.modules]
    assert "src/reforge/domain/models.py" in modules_norm
    assert "src/reforge/domain/interfaces.py" in modules_norm
    assert "src/reforge/usecases/scout.py" in modules_norm
    assert "src/reforge/adapters/repositories.py" in modules_norm

    # Check component list
    assert set(report.components) == {"domain", "usecases", "adapters"}

    # Assert dependency couplings are correctly resolved
    # models has no internal dependencies
    models_key = [k for k in report.dependencies.keys() if "models.py" in k][0]
    assert len(report.dependencies[models_key]) == 0

    # interfaces depends on models
    interfaces_key = [k for k in report.dependencies.keys() if "interfaces.py" in k][0]
    assert len(report.dependencies[interfaces_key]) == 1
    assert any("models.py" in dep for dep in report.dependencies[interfaces_key])

    # Check relationships
    assert "usecases -> domain" in report.relationships
    assert "usecases -> interfaces" in report.relationships
    assert "adapters -> interfaces" in report.relationships
