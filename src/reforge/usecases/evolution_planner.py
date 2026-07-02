import uuid
from datetime import datetime
from reforge.domain.interfaces import ArchaeologyAgent
from reforge.domain.models import AgentLog, ExcavationState, ExcavationStatus, EvolutionSuggestion, EvolutionReport

class EvolutionPlannerAgent(ArchaeologyAgent):
    """The agent responsible for Stage 8 — Evolution Planning.

    Formulates long-term improvement options (performance, security, features) tailored to the
    specific repository architecture, dependencies, and component coupling graphs.
    """

    @property
    def name(self) -> str:
        return "Evolution Planner"

    async def run(self, state: ExcavationState) -> EvolutionReport:
        if not state.software_overview:
            raise ValueError("ExcavationState must contain a software_overview to perform Evolution Planning.")

        # Transition status
        state.status = ExcavationStatus.EVOLVING
        state.updated_at = datetime.utcnow()

        input_params = {
            "project_id": state.project_id,
            "has_architecture": str(state.architecture_report is not None)
        }

        try:
            suggestions = []
            overview = state.software_overview

            # Heuristic 1: Lock files (Always check if lock files are missing)
            has_lock_file = False
            for folder, files in overview.directory_tree.items():
                for f in files:
                    if f.lower() in ("poetry.lock", "package-lock.json", "yarn.lock", "cargo.lock", "go.sum"):
                        has_lock_file = True
                        break
            
            if not has_lock_file:
                suggestions.append(EvolutionSuggestion(
                    suggestion_type="performance_improvement",
                    title="Integrate Modern Dependency Lock Files",
                    description="The project uses basic package manifests without locking dependencies (e.g. poetry.lock, package-lock.json).",
                    benefit="Ensures deterministic environment installations across all production and developer machines.",
                    difficulty="EASY"
                ))

            # Heuristic 2: Linter and static security analyzers
            has_lint_config = False
            for folder, files in overview.directory_tree.items():
                for f in files:
                    if any(marker in f.lower() for marker in (".eslintrc", "ruff.toml", "pyproject.toml", "setup.cfg", ".flake8")):
                        has_lint_config = True
                        break
            
            if not has_lint_config:
                suggestions.append(EvolutionSuggestion(
                    suggestion_type="security_improvement",
                    title="Configure Automated Linter and Code Quality Guards",
                    description="No static analysis checkers or style formatters (like Black, Ruff, ESLint) were identified.",
                    benefit="Prevents code regression, enforces standard naming conventions, and blocks common security vulnerability patterns in CI/CD pipelines.",
                    difficulty="EASY"
                ))

            # Heuristic 3: Architecture Paradigm specific suggestion
            paradigm = getattr(overview, "architecture_paradigm", "Layered/Generic")
            if "Command-Line" in paradigm:
                suggestions.append(EvolutionSuggestion(
                    suggestion_type="framework_upgrade",
                    title="Modernize Command-Line Parsing with Typer",
                    description="The codebase is identified as a CLI Utility. Migrating to Typer leverages Python type hints for auto-completions, nested commands, and clean interface structures.",
                    benefit="Reduces boilerplate parsing logic and provides self-documenting cli help menus.",
                    difficulty="MEDIUM"
                ))
            elif paradigm == "Clean Architecture":
                suggestions.append(EvolutionSuggestion(
                    suggestion_type="new_capability",
                    title="Enforce Architectural Boundary Testing rules",
                    description="The project implements Clean Architecture. Add import-dependency enforcement checkers (like import-linter) to verify domain layer remains decoupled.",
                    benefit="Statically blocks adapter or infrastructure details from bleeding back into domain files.",
                    difficulty="MEDIUM"
                ))
            elif paradigm == "MVC (Model-View-Controller)":
                suggestions.append(EvolutionSuggestion(
                    suggestion_type="framework_upgrade",
                    title="Decouple View rendering to Client-Side API Architecture",
                    description="The project uses monolithic MVC. Decouple view controllers into a separate single-page application (SPA) front-end communicating via REST API.",
                    benefit="Enables independent frontend/backend scaling and facilitates native web app integrations.",
                    difficulty="HARD"
                ))
            else:
                # Fallback to framework checks for generic layered layouts
                has_async_framework = any(fw in ["FastAPI", "Express"] for fw in overview.frameworks)
                if has_async_framework:
                    suggestions.append(EvolutionSuggestion(
                        suggestion_type="framework_upgrade",
                        title="Adopt Fully Asynchronous Database Connections",
                        description="The codebase leverages async web frameworks but lacks async DB drivers.",
                        benefit="Drastically increases API throughput by avoiding blocking threads during database queries.",
                        difficulty="MEDIUM"
                    ))
                else:
                    suggestions.append(EvolutionSuggestion(
                        suggestion_type="new_capability",
                        title="Implement Clean Architecture Directory Layout",
                        description="No major application frameworks were detected. The project directory layout would benefit from structural separation of concerns.",
                        benefit="Decouples business validation logic from database and transport boundary changes.",
                        difficulty="HARD"
                    ))

            # Heuristic 4: Component Coupling Density suggestions
            if state.architecture_report:
                rel_count = len(state.architecture_report.relationships)
                if rel_count > 10:
                    suggestions.append(EvolutionSuggestion(
                        suggestion_type="refactoring_proposal",
                        title="Decouple Tightly Coupled Component Layers",
                        description=f"High inter-component dependency density was discovered ({rel_count} inter-layer coupling connections).",
                        benefit="Reduces side-effects during updates, improves modular testing, and makes codebase easier to extend.",
                        difficulty="HARD"
                    ))

            # Heuristic 5: Testing validation warnings
            if state.validation_report and not state.validation_report.pytest_discovered:
                suggestions.append(EvolutionSuggestion(
                    suggestion_type="new_capability",
                    title="Integrate Automated Unit Testing Suite",
                    description="No Python test suite configuration was discovered during Stage 7 Validation checks.",
                    benefit="Increases software preservation feasibility and protects the codebase against syntax regression.",
                    difficulty="MEDIUM"
                ))

            # Fallback if no specific recommendations generated
            if not suggestions:
                suggestions.append(EvolutionSuggestion(
                    suggestion_type="performance_improvement",
                    title="Optimize Python Module Import Runtimes",
                    description="Optimize standard library dependencies loading procedures.",
                    benefit="Decreases initialization and execution startup latency.",
                    difficulty="EASY"
                ))

            explanation = (
                f"Generated {len(suggestions)} evolution suggestions for the project. "
                f"Included recommendations for package lock integrations, code quality linting, and framework-specific upgrades."
            )

            report = EvolutionReport(
                suggestions=suggestions,
                explanation=explanation
            )

            # Save state
            state.evolution_report = report
            state.status = ExcavationStatus.COMPLETED
            state.updated_at = datetime.utcnow()

            # Record Agent Log
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="EVOLUTION_PLANNING",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=report.model_dump_json(indent=2),
                explanation=explanation
            )
            state.audit_logs.append(log_entry)
            return report

        except Exception as err:
            state.status = ExcavationStatus.FAILED
            state.updated_at = datetime.utcnow()
            error_message = f"{type(err).__name__}: {str(err)}"
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="EVOLUTION_PLANNING_FAILED",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=error_message,
                explanation=f"Evolution planning compilation failed. Error: {error_message}"
            )
            state.audit_logs.append(log_entry)
            raise err
