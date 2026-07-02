import os
import pytest
from reforge.adapters.workspace_inspector import LocalWorkspaceInspector

@pytest.mark.asyncio
async def test_local_workspace_inspector(tmp_path):
    # Setup mock file structure in tmp_path
    
    # 1. Create README
    readme = tmp_path / "README.md"
    readme.write_text("# My Cool Project\nBuilt with FastAPI.", encoding="utf-8")
    
    # 2. Create requirements.txt
    reqs = tmp_path / "requirements.txt"
    reqs.write_text("fastapi>=0.100.0\npytest==7.0.0\n# comment\ndjango\n", encoding="utf-8")
    
    # 3. Create entry point main.py
    main_py = tmp_path / "main.py"
    main_py.write_text("import fastapi", encoding="utf-8")

    # 4. Create subfolder with docs
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    install_md = docs_dir / "install.md"
    install_md.write_text("# Installation", encoding="utf-8")

    # 5. Create some files in source
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    app_py = src_dir / "app.py"
    app_py.write_text("app = None", encoding="utf-8")

    # Run inspector
    inspector = LocalWorkspaceInspector()
    overview = await inspector.inspect(str(tmp_path))

    # Assertions
    assert overview.build_system == "pip"
    assert set(overview.dependencies) == {"fastapi", "pytest", "django"}
    assert set(overview.frameworks) == {"FastAPI", "Django"}
    
    # Check entry points (paths should be relative to workspace root)
    assert "main.py" in overview.entry_points
    assert "src/app.py" in [p.replace("\\", "/") for p in overview.entry_points]

    # Check documentation files
    docs_norm = [p.replace("\\", "/") for p in overview.documentation_files]
    assert "README.md" in docs_norm
    assert "docs/install.md" in docs_norm

    # Check directory tree has children
    assert "" in overview.directory_tree
    assert "README.md" in overview.directory_tree[""]
    assert "docs" in overview.directory_tree


@pytest.mark.asyncio
async def test_local_workspace_inspector_architecture_paradigms(tmp_path):
    # Setup Clean Architecture structure in tmp_path/clean
    clean_dir = tmp_path / "clean"
    os.makedirs(clean_dir / "domain", exist_ok=True)
    os.makedirs(clean_dir / "adapters", exist_ok=True)
    os.makedirs(clean_dir / "infrastructure", exist_ok=True)
    (clean_dir / "README.md").write_text("# Clean Project", encoding="utf-8")

    inspector = LocalWorkspaceInspector()
    clean_overview = await inspector.inspect(str(clean_dir))
    assert clean_overview.architecture_paradigm == "Clean Architecture"

    # Setup MVC structure in tmp_path/mvc
    mvc_dir = tmp_path / "mvc"
    os.makedirs(mvc_dir / "models", exist_ok=True)
    os.makedirs(mvc_dir / "views", exist_ok=True)
    os.makedirs(mvc_dir / "controllers", exist_ok=True)
    (mvc_dir / "README.md").write_text("# MVC Project", encoding="utf-8")

    mvc_overview = await inspector.inspect(str(mvc_dir))
    assert mvc_overview.architecture_paradigm == "MVC (Model-View-Controller)"
