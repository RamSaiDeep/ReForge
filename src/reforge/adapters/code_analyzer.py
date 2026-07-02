import os
import re
import ast
from typing import Dict, List, Set
from reforge.domain.interfaces import CodeAnalyzer
from reforge.domain.models import ArchitectureReport

class LocalCodeAnalyzer(CodeAnalyzer):
    """Concrete implementation of CodeAnalyzer traversing source files.

    Performs AST-based import analysis to map internal module couplings and architectural layer relationships.
    """

    def __init__(self) -> None:
        self.exclude_dirs = {".git", ".venv", "node_modules", "__pycache__", "venv", "env", "build", "dist"}

    def _get_module_key(self, file_path: str, base_path: str) -> str:
        """Translate local file path to a clean relative path key (e.g. src/main.py)."""
        rel_path = os.path.relpath(file_path, base_path)
        return rel_path.replace("\\", "/")

    def _parse_python_imports(self, file_path: str, rel_key: str) -> List[str]:
        """Scan python files using abstract syntax trees to extract import statements."""
        imports = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            tree = ast.parse(content, filename=file_path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.level > 0:
                        # Handle relative imports: e.g. from ..domain.models import X
                        parts = rel_key.split("/")
                        # Slice off file name and the number of relative dots
                        package_parts = parts[:-1]
                        if node.level <= len(package_parts):
                            parent_parts = package_parts[:-(node.level - 1)] if node.level > 1 else package_parts
                            rel_module = ".".join(parent_parts)
                            if node.module:
                                imports.append(f"{rel_module}.{node.module}")
                            else:
                                imports.append(rel_module)
                        else:
                            if node.module:
                                imports.append(node.module)
                    else:
                        if node.module:
                            imports.append(node.module)
        except Exception:
            # Fallback to regex-based parser if AST parsing fails
            imports = self._parse_python_imports_regex_fallback(file_path)
        return imports

    def _parse_python_imports_regex_fallback(self, file_path: str) -> List[str]:
        """Regex-based fallback parser if AST parsing fails."""
        imports = []
        import_pattern = re.compile(r"^\s*import\s+([a-zA-Z0-9_\.,\s]+)")
        from_pattern = re.compile(r"^\s*from\s+([a-zA-Z0-9_\.]+)\s+import")

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    imp_match = import_pattern.match(line)
                    if imp_match:
                        parts = [p.strip() for p in imp_match.group(1).split(",")]
                        imports.extend(parts)
                    from_match = from_pattern.match(line)
                    if from_match:
                        imports.append(from_match.group(1))
        except Exception:
            pass
        return imports

    def _resolve_internal_dependency(self, imported_module: str, all_modules: Set[str]) -> List[str]:
        """Determine if an import name refers to any of our internal modules.

        E.g., if we import 'reforge.domain.models', does it match 'src/reforge/domain/models.py'?
        """
        resolved = []
        module_path_part = imported_module.replace(".", "/")
        
        for mod in all_modules:
            mod_no_ext, _ = os.path.splitext(mod)
            # Match exact match or tail match
            if mod_no_ext == module_path_part or mod_no_ext.endswith("/" + module_path_part) or mod_no_ext.endswith(module_path_part):
                resolved.append(mod)
        return resolved

    def _get_component_name(self, relative_path: str) -> str:
        """Deduce high-level component name from path directories."""
        parts = relative_path.split("/")
        if len(parts) > 1:
            if parts[0] == "src" and len(parts) > 2:
                if len(parts) > 3 and parts[1].isidentifier():
                    return parts[2]
                return parts[1]
            return parts[0]
        return "Root"

    async def analyze(self, local_path: str) -> ArchitectureReport:
        if not os.path.exists(local_path):
            raise ValueError(f"Target path does not exist: {local_path}")

        all_file_modules: Dict[str, str] = {} # maps clean relative key to absolute path
        
        # 1. Discover all source files
        for root, dirs, files in os.walk(local_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            for file in files:
                if file.endswith(".py"): # focus on Python architecture
                    abs_path = os.path.join(root, file)
                    rel_key = self._get_module_key(abs_path, local_path)
                    all_file_modules[rel_key] = abs_path

        modules_list = list(all_file_modules.keys())
        all_modules_set = set(modules_list)
        
        dependencies_graph: Dict[str, List[str]] = {}
        components_set: Set[str] = set()
        relationships_set: Set[str] = set()

        # 2. Extract dependencies and components
        for rel_key, abs_path in all_file_modules.items():
            comp = self._get_component_name(rel_key)
            components_set.add(comp)
            
            raw_imports = self._parse_python_imports(abs_path, rel_key)
            
            # Resolve raw imports to internal modules
            internal_deps = []
            for imp in raw_imports:
                resolved_mods = self._resolve_internal_dependency(imp, all_modules_set)
                for resolved in resolved_mods:
                    if resolved != rel_key: # avoid self-imports
                        internal_deps.append(resolved)

            # Deduplicate dependencies
            unique_deps = sorted(list(set(internal_deps)))
            dependencies_graph[rel_key] = unique_deps

            # Track component relationships
            for dep in unique_deps:
                dep_comp = self._get_component_name(dep)
                if comp != dep_comp:
                    relationships_set.add(f"{comp} -> {dep_comp}")

        components_list = sorted(list(components_set))
        relationships_list = sorted(list(relationships_set))

        # Generate explainable summary
        explanation = (
            f"Successfully reconstructed software architecture. Identified {len(modules_list)} source modules "
            f"grouped across {len(components_list)} component layers ({', '.join(components_list) if components_list else 'None'}). "
            f"Mapped {sum(len(v) for v in dependencies_graph.values())} internal module import coupling connections. "
            f"Discovered component dependency boundaries: {', '.join(relationships_list) if relationships_list else 'No inter-component links'}."
        )

        return ArchitectureReport(
            modules=modules_list,
            dependencies=dependencies_graph,
            components=components_list,
            relationships=relationships_list,
            explanation=explanation
        )
