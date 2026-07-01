import json
import os
import re
from typing import Dict, List, Optional, Set
from reforge.domain.interfaces import WorkspaceInspector
from reforge.domain.models import SoftwareOverview

class LocalWorkspaceInspector(WorkspaceInspector):
    """Concrete implementation of WorkspaceInspector crawling local directory files."""

    def __init__(self) -> None:
        self.exclude_dirs = {".git", ".venv", "node_modules", "__pycache__", "venv", "env", "build", "dist"}
        self.doc_extensions = {".md", ".rst", ".txt"}

    def _parse_requirements_txt(self, path: str) -> List[str]:
        """Simple line parser for Python requirements.txt."""
        dependencies = []
        if not os.path.exists(path):
            return dependencies
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments or empty lines
                    if not line or line.startswith("#") or line.startswith("-r"):
                        continue
                    # Match package name before any version specifier (e.g., package>=1.0)
                    match = re.match(r"^([a-zA-Z0-9_\-\[\]]+)", line)
                    if match:
                        dependencies.append(match.group(1))
        except Exception:
            pass
        return dependencies

    def _parse_package_json(self, path: str) -> List[str]:
        """Simple JSON key parser for NodeJS dependencies."""
        dependencies = []
        if not os.path.exists(path):
            return dependencies
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                deps = data.get("dependencies", {})
                dev_deps = data.get("devDependencies", {})
                dependencies.extend(deps.keys())
                dependencies.extend(dev_deps.keys())
        except Exception:
            pass
        return dependencies

    def _detect_frameworks(self, dependencies: List[str], file_set: Set[str]) -> List[str]:
        """Deduce frameworks based on dependencies or key file markers."""
        frameworks = []
        dep_set = {dep.lower() for dep in dependencies}

        # Python frameworks
        if "django" in dep_set:
            frameworks.append("Django")
        if "flask" in dep_set:
            frameworks.append("Flask")
        if "fastapi" in dep_set:
            frameworks.append("FastAPI")

        # JS frameworks
        if "react" in dep_set:
            frameworks.append("React")
        if "vue" in dep_set:
            frameworks.append("Vue")
        if "express" in dep_set:
            frameworks.append("Express")

        # Java / general
        if "spring-boot" in dep_set or any("SpringBoot" in f for f in file_set):
            frameworks.append("Spring Boot")

        return frameworks

    async def inspect(self, local_path: str) -> SoftwareOverview:
        if not os.path.exists(local_path):
            raise ValueError(f"Target path does not exist: {local_path}")

        entry_points: List[str] = []
        dependencies: List[str] = []
        frameworks: List[str] = []
        build_system: Optional[str] = None
        directory_tree: Dict[str, List[str]] = {}
        documentation_files: List[str] = []
        file_set: Set[str] = set()

        common_entry_filenames = {"main.py", "app.py", "index.js", "server.js", "main.go", "index.ts", "App.java"}

        for root, dirs, files in os.walk(local_path):
            # Prune excluded directories in place
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            rel_root = os.path.relpath(root, local_path)
            if rel_root == ".":
                rel_root = ""

            # Populate directory tree (cap to avoid bloat)
            if len(directory_tree) < 50:
                directory_tree[rel_root] = files

            for file in files:
                file_set.add(file)
                file_path = os.path.join(root, file)
                rel_file_path = os.path.join(rel_root, file) if rel_root else file

                # Detect entry points
                if file in common_entry_filenames:
                    entry_points.append(rel_file_path)

                # Collect documentation files
                _, ext = os.path.splitext(file)
                if ext.lower() in self.doc_extensions:
                    documentation_files.append(rel_file_path)

                # Detect build configurations & parse dependencies
                if file == "requirements.txt":
                    build_system = "pip"
                    dependencies.extend(self._parse_requirements_txt(file_path))
                elif file == "package.json":
                    build_system = "npm"
                    dependencies.extend(self._parse_package_json(file_path))
                elif file == "Cargo.toml" and not build_system:
                    build_system = "cargo"
                elif file == "CMakeLists.txt" and not build_system:
                    build_system = "cmake"
                elif file == "pom.xml" and not build_system:
                    build_system = "maven"
                elif file == "build.gradle" and not build_system:
                    build_system = "gradle"
                elif file == "go.mod" and not build_system:
                    build_system = "go modules"
                elif file == "pyproject.toml" and not build_system:
                    build_system = "poetry/pip"

        # Detect frameworks based on parsed requirements & files
        frameworks = self._detect_frameworks(dependencies, file_set)

        # Generate explainable summary
        detected_build = build_system or "No standard build system detected"
        found_deps_count = len(dependencies)
        found_docs_count = len(documentation_files)
        
        explanation = (
            f"Successfully crawled repository workspace. Detected build system: {detected_build}. "
            f"Found {found_deps_count} library dependencies, {len(frameworks)} frameworks ({', '.join(frameworks) if frameworks else 'None'}), "
            f"and {found_docs_count} documentation files. "
            f"Entry point candidates discovered: {', '.join(entry_points) if entry_points else 'None'}."
        )

        return SoftwareOverview(
            entry_points=entry_points,
            dependencies=dependencies,
            frameworks=frameworks,
            build_system=build_system,
            directory_tree=directory_tree,
            documentation_files=documentation_files,
            explanation=explanation
        )
