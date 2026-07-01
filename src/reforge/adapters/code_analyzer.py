import os
import re
from typing import Dict, List, Set
from reforge.domain.interfaces import CodeAnalyzer
from reforge.domain.models import ArchitectureReport

class LocalCodeAnalyzer(CodeAnalyzer):
    """Concrete implementation of CodeAnalyzer traversing source files.

    Performs regex-based import analysis to map internal module couplings and architectural layer relationships.
    """

    def __init__(self) -> None:
        self.exclude_dirs = {".git", ".venv", "node_modules", "__pycache__", "venv", "env", "build", "dist"}

    def _get_module_key(self, file_path: str, base_path: str) -> str:
        """Translate local file path to a clean relative path key (e.g. src/main.py)."""
        rel_path = os.path.relpath(file_path, base_path)
        return rel_path.replace("\\", "/")

    def _parse_python_imports(self, file_path: str) -> List[str]:
        """Scan python files for import statements."""
        imports = []
        import_pattern = re.compile(r"^\s*import\s+([a-zA-Z0-9_\.,\s]+)")
        from_pattern = re.compile(r"^\s*from\s+([a-zA-Z0-9_\.]+)\s+import")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    # Match standard 'import x'
                    imp_match = import_pattern.match(line)
                    if imp_match:
                        # Split multiple imports on comma (e.g., import os, sys)
                        parts = [p.strip() for p in imp_match.group(1).split(",")]
                        imports.extend(parts)
                    # Match 'from y import z'
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
        # Convert import representation (reforge.domain.models) to path-like (reforge/domain/models)
        module_path_part = imported_module.replace(".", "/")
        
        for mod in all_modules:
            # Strip file extension
            mod_no_ext, _ = os.path.splitext(mod)
            if mod_no_ext.endswith(module_path_part) or module_path_part in mod_no_ext:
                resolved.append(mod)
        return resolved

    def _get_component_name(self, relative_path: str) -> str:
        """Deduce high-level component name from path directories."""
        parts = relative_path.split("/")
        if len(parts) > 1:
            # If path is src/reforge/domain/models.py, 'domain' or first folder under src/reforge is key
            # Let's clean commonly nested packages: src/reforge/domain -> domain
            if parts[0] == "src" and len(parts) > 2:
                # E.g. src/reforge/domain/models.py -> 'domain' or second folder
                # Let's inspect: if parts[1] is package name (like reforge) and parts[2] is directory
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
            
            raw_imports = self._parse_python_imports(abs_path)
            
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
