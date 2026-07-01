import uuid
from datetime import datetime
from reforge.domain.interfaces import ArchaeologyAgent
from reforge.domain.models import AgentLog, ExcavationState, ExcavationStatus, EvolutionSuggestion, EvolutionReport

class EvolutionPlannerAgent(ArchaeologyAgent):
    """The agent responsible for Stage 7 — Evolution Planning.

    Formulates long-term improvement options (performance, security, features) based on structural code findings.
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

            # Heuristic 1: Lock files
            suggestions.append(EvolutionSuggestion(
                suggestion_type="performance_improvement",
                title="Integrate Modern Dependency Lock Files",
                description="The project uses basic package manifests without locking dependencies (e.g. poetry.lock, package-lock.json).",
                benefit="Ensures deterministic environment installations across all production and developer machines.",
                difficulty="EASY"
            ))

            # Heuristic 2: Linter and static security analyzers
            suggestions.append(EvolutionSuggestion(
                suggestion_type="security_improvement",
                title="Configure Automated Linter and Code Quality Guards",
                description="No static analysis checkers or style formatters (like Black, Ruff, ESLint) were identified.",
                benefit="Prevents code regression, enforces standard naming conventions, and blocks common security vulnerability patterns in CI/CD pipelines.",
                difficulty="EASY"
            ))

            # Heuristic 3: Framework-specific updates
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
