import uuid
from datetime import datetime
from reforge.domain.interfaces import ArchaeologyAgent
from reforge.domain.models import AgentLog, ExcavationState, ExcavationStatus, RestorationIssue, RestorationPlan

class RestorationPlannerAgent(ArchaeologyAgent):
    """The agent responsible for Stage 5 — Restoration Planning.

    Analyzes software overviews and architecture dependency graphs to deduce missing libraries,
    build configuration issues, and document a step-by-step restoration strategy.
    """

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

            # Rule 4: Structural dependency loops / density (from Stage 4 report)
            if state.architecture_report:
                report = state.architecture_report
                # If there are component layers but no relationships defined
                if report.components and not report.relationships:
                    issues.append(RestorationIssue(
                        issue_type="compatibility_issue",
                        description="Component folders exist but they are completely decoupled. Verify module mappings.",
                        severity="LOW",
                        recommended_fix="Review folders and add package initializers (__init__.py) where needed."
                    ))

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
                effort = 0.5 # default small effort for a clean checkout

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
            # Advance to awaiting approval stage (representing pipeline waiting for human review)
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
