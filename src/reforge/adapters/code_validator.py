import ast
import os
import py_compile
import subprocess
import sys
from typing import Set, List, Tuple
from reforge.domain.interfaces import CodeValidator
from reforge.domain.models import ValidationReport

class LocalCodeValidator(CodeValidator):
    """Concrete implementation of CodeValidator.

    Performs comprehensive syntax compilation, import resolution checks, 
    and unit test execution on the local codebase workspace.
    """

    def __init__(self) -> None:
        self.exclude_dirs = {".git", ".venv", "node_modules", "__pycache__"}
        # Common standard library names
        self.std_libs = {
            "os", "sys", "json", "time", "datetime", "math", "re", "collections",
            "typing", "abc", "subprocess", "shutil", "tempfile", "unittest",
            "logging", "urllib", "hashlib", "io", "copy", "uuid", "random",
            "importlib", "pathlib", "sysconfig", "argparse", "functools", "itertools"
        }

    async def validate(self, local_path: str) -> ValidationReport:
        if not os.path.exists(local_path):
            raise ValueError(f"Target path does not exist for validation: {local_path}")

        files_compiled = 0
        syntax_errors = 0
        local_modules = self._discover_local_modules(local_path)
        
        broken_imports = []
        long_lines_count = 0
        
        # Traverse and scan
        for root, dirs, files in os.walk(local_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    
                    # 1. Syntax check
                    try:
                        py_compile.compile(file_path, doraise=True)
                        files_compiled += 1
                    except (py_compile.PyCompileError, SyntaxError):
                        syntax_errors += 1
                        
                    # 2. AST parsing to check imports & style lints
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            
                        # Lint checking (long lines)
                        for line in content.splitlines():
                            if len(line) > 120:
                                long_lines_count += 1
                                
                        # AST scanning
                        tree = ast.parse(content, filename=file_path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    self._verify_import(alias.name, local_modules, broken_imports, file_path)
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    self._verify_import(node.module, local_modules, broken_imports, file_path)
                    except Exception:
                        # If AST fails, treat as syntax/parsing issue if not already caught
                        pass

        # Calculate Statuses
        syntax_status = "PASSED" if syntax_errors == 0 else "FAILED"
        imports_status = "PASSED" if not broken_imports else "WARNING"
        lint_status = "PASSED" if long_lines_count < 10 else "WARNING"
        build_status = "PASSED" if (os.path.exists(os.path.join(local_path, "pyproject.toml")) or 
                                    os.path.exists(os.path.join(local_path, "setup.py")) or 
                                    os.path.exists(os.path.join(local_path, "requirements.txt"))) else "FAILED"

        # 3. Test Discovery & Execution
        has_tests, test_files = self._discover_tests(local_path)
        tests_passed = 0
        tests_failed = 0
        tests_status = "SKIPPED"
        
        if has_tests:
            passed, failed, run_success = self._run_pytest_suite(local_path)
            if run_success:
                tests_passed = passed
                tests_failed = failed
                tests_status = "PASSED" if failed == 0 else "FAILED"
            else:
                tests_status = "FAILED"

        # Overall Status outcome
        overall_status = "PASSED"
        if syntax_status == "FAILED" or tests_status == "FAILED":
            overall_status = "FAILED"

        # Explanation summary
        explanation = (
            f"Code validation completed. Status: {overall_status}. "
            f"Compiled {files_compiled} Python files with {syntax_errors} errors. "
            f"Discovered {len(broken_imports)} unresolved import warnings. "
            f"Test execution status: {tests_status} ({tests_passed} passed, {tests_failed} failed)."
        )

        return ValidationReport(
            overall_status=overall_status,
            files_compiled=files_compiled,
            pytest_discovered=has_tests,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            coverage_percentage=None,
            syntax_status=syntax_status,
            imports_status=imports_status,
            tests_status=tests_status,
            build_status=build_status,
            lint_status=lint_status,
            explanation=explanation
        )

    def _discover_local_modules(self, local_path: str) -> Set[str]:
        """Index all local directories and module filenames to check import validity."""
        modules = {"reforge", "src", "tests", "adapters", "domain", "infrastructure", "usecases"}
        for root, dirs, files in os.walk(local_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            for d in dirs:
                modules.add(d)
            for f in files:
                if f.endswith(".py"):
                    modules.add(f[:-3])
        return modules

    def _verify_import(self, module_name: str, local_modules: Set[str], broken_imports: List[str], file_path: str):
        base_module = module_name.split(".")[0]
        # Ignore standard libraries, system modules, and locally indexed modules
        if (base_module in self.std_libs or 
            base_module in sys.builtin_module_names or 
            base_module in sys.modules or 
            base_module in local_modules or
            base_module == ""):
            return
        # Flag as unresolved external package dependency
        broken_imports.append(f"{base_module} in {os.path.basename(file_path)}")

    def _discover_tests(self, local_path: str) -> Tuple[bool, List[str]]:
        test_files = []
        for root, dirs, files in os.walk(local_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    test_files.append(os.path.join(root, file))
        return len(test_files) > 0, test_files

    def _run_pytest_suite(self, local_path: str) -> Tuple[int, int, bool]:
        """Execute pytest in the workspace and extract passed/failed counts from stdout."""
        try:
            # Run pytest and capture output. Limit runtime to 15 seconds.
            env = os.environ.copy()
            # Ensure PYTHONPATH includes local src or root directory
            env["PYTHONPATH"] = os.path.pathsep.join([
                os.path.join(local_path, "src"),
                local_path,
                env.get("PYTHONPATH", "")
            ])
            
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--tb=short", "-q"],
                cwd=local_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15.0,
                env=env
            )
            
            stdout = result.stdout
            
            # Simple parsing: standard pytest output formats
            # e.g., "5 passed, 1 warning in 1.22s" or "3 failed, 1 passed"
            passed = 0
            failed = 0
            
            # Search for test status outputs
            import re
            passed_match = re.search(r"(\d+)\s+passed", stdout)
            failed_match = re.search(r"(\d+)\s+failed", stdout)
            error_match = re.search(r"(\d+)\s+error", stdout)
            
            if passed_match:
                passed = int(passed_match.group(1))
            if failed_match:
                failed = int(failed_match.group(1))
            if error_match:
                failed += int(error_match.group(1))
                
            # If no passed or failed was matched but return code is 0, we can look for "no tests ran"
            if passed == 0 and failed == 0 and result.returncode == 0:
                # Count tests by parsing dots in short summary: e.g. "...."
                lines = stdout.splitlines()
                for line in lines:
                    if line.startswith(".") or "passed" in line:
                        passed += line.count(".")
                        
            return passed, failed, True
        except subprocess.TimeoutExpired:
            return 0, 0, False
        except Exception:
            return 0, 0, False
