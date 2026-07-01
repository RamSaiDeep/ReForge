import uuid
from datetime import datetime
from reforge.domain.interfaces import ArchaeologyAgent, CodeAnalyzer
from reforge.domain.models import AgentLog, ArchitectureReport, ExcavationState, ExcavationStatus

class ArchitectAgent(ArchaeologyAgent):
    """The agent responsible for Stage 4 — Architecture Reconstruction.

    Inspects the cloned project workspace and reconstructs the software's internal dependencies.
    """

    def __init__(self, analyzer: CodeAnalyzer) -> None:
        self.analyzer = analyzer

    @property
    def name(self) -> str:
        return "Software Architect"

    async def run(self, state: ExcavationState) -> ArchitectureReport:
        if not state.local_path:
            raise ValueError("ExcavationState must contain a local_path to run Architecture Reconstruction.")

        state.status = ExcavationStatus.RECONSTRUCTING
        state.updated_at = datetime.utcnow()

        input_params = {
            "project_id": state.project_id,
            "local_path": state.local_path
        }

        try:
            # Reconstruct the code dependency structure
            report = await self.analyzer.analyze(state.local_path)
            
            # Save state
            state.architecture_report = report
            state.status = ExcavationStatus.RECONSTRUCTED
            state.updated_at = datetime.utcnow()

            # Record Agent Log
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="ARCHITECTURE_RECONSTRUCTION",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=report.model_dump_json(indent=2),
                explanation=report.explanation
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
                action_type="ARCHITECTURE_RECONSTRUCTION_FAILED",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=error_message,
                explanation=f"Architecture reconstruction failed during dependency parsing. Error: {error_message}"
            )
            state.audit_logs.append(log_entry)
            raise err
