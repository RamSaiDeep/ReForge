import uuid
import os
import re
from datetime import datetime
from reforge.domain.interfaces import ArchaeologyAgent
from reforge.domain.models import AgentLog, ExcavationState, ExcavationStatus, RestorationIssue, RestorationPlan

class RestorationPlannerAgent(ArchaeologyAgent):
    """The agent responsible for Stage 5 — Restoration Planning.

    Analyzes software overviews and architecture dependency graphs to deduce missing libraries,
    build configuration issues, deprecated APIs, target version limits, and documents a
    step-by-step restoration strategy.
    """

    def __init__(self) -> None:
        self.exclude_dirs = {".git", ".venv", "node_modules", "__pycache__"}

    @property
    def name(self) -> str:
        return "Restoration Planner"

    async def run(self, state: ExcavationState) -> RestorationPlan:
        if not state.software_overview:
            raise ValueError("ExcavationState must contain a software_overview to perform Restoration Planning.")

        # Transition to planning stage
        state.status = ExcavationStatus.RESTORATION_PLANNING
        state.updated_at = datetime.utcnow()

        input_params = {
            "project_id": state.project_id,
            "build_system": str(state.software_overview.build_system),
            "has_architecture": str(state.architecture_report is not None)
        }

        try:
            issues = []
            steps = []
            
            overview = state.software_overview
            
            # Helper to check file existence in directory tree
            def file_exists(filename: str) -> bool:
                upper_name = filename.upper()
                for folder, files in overview.directory_tree.items():
                    for f in files:
                        if f.upper() == upper_name or f.upper().endswith("/" + upper_name) or f.upper().endswith("\\" + upper_name):
                            return True
                return False

            # Rule 1: Detect missing build system configuration
            if not overview.build_system:
                issues.append(RestorationIssue(
                    issue_type="build_failure",
                    description="No recognizable build system configuration file (e.g. requirements.txt, package.json) was identified in the project root.",
                    severity="HIGH",
                    recommended_fix="Initialize a package manifest (e.g. requirements.txt for Python, package.json for Node.js) listing core modules."
                ))
                steps.append("Identify primary language and configure a build system file (e.g. requirements.txt / package.json)")
            else:
                # Add default setup steps based on detected build system
                if overview.build_system == "pip":
                    steps.append("Create python virtual environment: python -m venv .venv")
                    steps.append("Activate virtual environment and upgrade pip: .venv\\Scripts\\pip install --upgrade pip")
                    steps.append("Install project dependencies: pip install -r requirements.txt")
                elif overview.build_system == "npm":
                    steps.append("Install node dependencies: npm install")
                elif overview.build_system == "cargo":
                    steps.append("Build rust executable: cargo build")
                else:
                    steps.append(f"Execute default restore command for build system: {overview.build_system}")

            # Rule 2: Empty dependencies warnings
            if not overview.dependencies:
                issues.append(RestorationIssue(
                    issue_type="missing_dependency",
                    description="The project dependencies list is empty. Importing code files might fail at runtime due to missing libraries.",
                    severity="MEDIUM",
                    recommended_fix="Scan codebase imports to compile a dependency list and populate the project manifest."
                ))
                steps.append("Perform manual import scan to compile missing dependency list")

            # Rule 3: Missing documentation files
            if not overview.documentation_files:
                issues.append(RestorationIssue(
                    issue_type="compatibility_issue",
                    description="No readme or documentation file exists in the repository. Build or runtime configurations might be unclear.",
                    severity="LOW",
                    recommended_fix="Create a README.md file in the root containing setup, execution, and project overview guides."
                ))
                steps.append("Create a README.md documenting system architecture and restore parameters")

            # Rule 4: Structural decoupled components (from Stage 4 report)
            if state.architecture_report:
                report = state.architecture_report
                if report.components and not report.relationships:
                    issues.append(RestorationIssue(
                        issue_type="compatibility_issue",
                        description="Component folders exist but they are completely decoupled. Verify module mappings.",
                        severity="LOW",
                        recommended_fix="Review folders and add package initializers (__init__.py) where needed."
                    ))

            # --- Extended Archaeological Checks ---

            # Rule 5: Missing Lock Files
            if overview.build_system == "pip" or file_exists("pyproject.toml"):
                if file_exists("pyproject.toml") and not file_exists("poetry.lock"):
                    issues.append(RestorationIssue(
                        issue_type="missing_lockfile",
                        description="Dependency lock file (poetry.lock) is missing. Restoring packages might install inconsistent package versions.",
                        severity="MEDIUM",
                        recommended_fix="Run 'poetry lock' to generate a consistent poetry.lock file."
                    ))
                    steps.append("Generate dependency lock file: poetry lock")
            elif file_exists("package.json"):
                if not file_exists("package-lock.json") and not file_exists("yarn.lock"):
                    issues.append(RestorationIssue(
                        issue_type="missing_lockfile",
                        description="Node dependency lock file (package-lock.json) is missing. Restoring packages might install inconsistent package versions.",
                        severity="MEDIUM",
                        recommended_fix="Run 'npm install' or 'npm shrinkwrap' to generate a package-lock.json file."
                    ))
                    steps.append("Generate node package lock file: npm install")

            # Rule 6: Missing CI/CD Configuration
            has_ci = False
            for folder in overview.directory_tree.keys():
                if ".github" in folder or "workflows" in folder or "gitlab-ci" in folder:
                    has_ci = True
                    break
            if not has_ci and overview.directory_tree:
                issues.append(RestorationIssue(
                    issue_type="missing_ci_config",
                    description="No automated continuous integration (CI/CD) pipelines were detected in the workspace.",
                    severity="LOW",
                    recommended_fix="Configure a CI workflow file (e.g. .github/workflows/ci.yml) to automate tests and syntax checks."
                ))
                steps.append("Configure automated CI workflow: create .github/workflows/ci.yml")

            # Rule 7: Missing Software License
            has_license = False
            for folder, files in overview.directory_tree.items():
                for f in files:
                    if f.upper() in ("LICENSE", "LICENSE.TXT", "LICENSE.MD", "COPYING"):
                        has_license = True
                        break
            if not has_license and overview.directory_tree:
                issues.append(RestorationIssue(
                    issue_type="missing_license",
                    description="No software license file (e.g., LICENSE, COPYING) was identified in the repository root.",
                    severity="LOW",
                    recommended_fix="Add a license file to define usage constraints and permissions."
                ))
                steps.append("Add project license file: create LICENSE")

            # Rule 8: Unsupported target Python constraints & Deprecated libraries
            if state.local_path and os.path.exists(state.local_path):
                self._run_file_level_checks(state.local_path, issues, steps)

            # Calculate estimated effort (LOW=1.5h, MEDIUM=3.0h, HIGH=6.0h)
            effort = 0.0
            for issue in issues:
                if issue.severity == "HIGH":
                    effort += 6.0
                elif issue.severity == "MEDIUM":
                    effort += 3.0
                else:
                    effort += 1.5

            if not issues:
                effort = 0.5

            explanation = (
                f"Generated restoration plan with {len(issues)} issues identified. "
                f"Total estimated restoration effort: {effort} engineering hours. "
                f"Formulated {len(steps)} sequential restoration setup steps."
            )

            # Assemble plan report
            plan = RestorationPlan(
                issues=issues,
                steps=steps,
                estimated_effort_hours=effort,
                explanation=explanation
            )

            # Save state
            state.restoration_plan = plan
            state.status = ExcavationStatus.AWAITING_APPROVAL
            state.updated_at = datetime.utcnow()

            # Record Agent Log
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="RESTORATION_PLANNING",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=plan.model_dump_json(indent=2),
                explanation=explanation
            )
            state.audit_logs.append(log_entry)
            return plan

        except Exception as err:
            state.status = ExcavationStatus.FAILED
            state.updated_at = datetime.utcnow()
            error_message = f"{type(err).__name__}: {str(err)}"
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="RESTORATION_PLANNING_FAILED",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=error_message,
                explanation=f"Restoration planning failed. Error: {error_message}"
            )
            state.audit_logs.append(log_entry)
            raise err

    def _run_file_level_checks(self, workspace_path: str, issues: list, steps: list):
        """Inspect physical source files inside workspace for version constraints and deprecated calls."""
        # 1. Target Python version constraints
        pyproject_path = os.path.join(workspace_path, "pyproject.toml")
        if os.path.exists(pyproject_path):
            try:
                with open(pyproject_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                # Search for target python constraints: e.g. python = "^3.7" or python = ">=3.7"
                match = re.search(r'python\s*=\s*"\D*3\.([0-7])"', content)
                if match:
                    minor_ver = match.group(1)
                    issues.append(RestorationIssue(
                        issue_type="unsupported_python_version",
                        description=f"Target Python version constraint '3.{minor_ver}' is outdated and unsupported by modern packages.",
                        severity="MEDIUM",
                        recommended_fix="Upgrade python target version in pyproject.toml / setup.py to '>=3.10'."
                    ))
                    steps.append("Upgrade target python version constraint to >=3.10")
            except Exception:
                pass

        # 2. Deprecated modules scan (imp, cgi, asyncore, pipes)
        deprecated_modules = {"imp", "cgi", "asyncore", "pipes"}
        found_dep = set()
        
        try:
            for root, dirs, files in os.walk(workspace_path):
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        
                        # Match: import imp  or  from imp import ...
                        for dep in deprecated_modules:
                            if re.search(rf"\b(import\s+{dep}\b|from\s+{dep}\s+import\b)", content):
                                found_dep.add(dep)
        except Exception:
            pass

        for dep in found_dep:
            issues.append(RestorationIssue(
                issue_type="deprecated_library",
                description=f"Deprecated Python library '{dep}' imported in codebase. This library is removed in modern Python 3.12+.",
                severity="HIGH",
                recommended_fix=f"Refactor imports and logic to use 'importlib' or standard modern replacements instead of '{dep}'."
            ))
            steps.append(f"Refactor deprecated Python imports: replace '{dep}' usage")
