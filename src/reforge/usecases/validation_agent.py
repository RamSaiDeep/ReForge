import uuid
from datetime import datetime
from reforge.domain.interfaces import ArchaeologyAgent, CodeValidator
from reforge.domain.models import AgentLog, ExcavationState, ExcavationStatus, ValidationReport

class ValidationAgent(ArchaeologyAgent):
    """The agent responsible for running compile/syntax checks to validate a restored codebase."""

    def __init__(self, validator: CodeValidator) -> None:
        self.validator = validator

    @property
    def name(self) -> str:
        return "Validation Agent"

    async def run(self, state: ExcavationState) -> ValidationReport:
        if not state.local_path:
            raise ValueError("ExcavationState must contain local_path to execute validation.")

        state.status = ExcavationStatus.VALIDATING
        state.updated_at = datetime.utcnow()

        input_params = {
            "project_id": state.project_id,
            "local_path": state.local_path
        }

        try:
            report = await self.validator.validate(state.local_path)
            state.validation_report = report
            
            if report.overall_status == "PASSED":
                state.status = ExcavationStatus.VALIDATED
                state.updated_at = datetime.utcnow()

                explanation = f"Successfully validated restored codebase. {report.explanation}"
                log_entry = AgentLog(
                    id=str(uuid.uuid4()),
                    project_id=state.project_id,
                    agent_name=self.name,
                    action_type="VALIDATION_SUCCESS",
                    timestamp=datetime.utcnow(),
                    input_parameters=input_params,
                    output_result=report.explanation,
                    explanation=explanation
                )
                state.audit_logs.append(log_entry)
                return report
            else:
                state.status = ExcavationStatus.FAILED
                state.updated_at = datetime.utcnow()

                explanation = f"Validation check failed: {report.explanation}"
                log_entry = AgentLog(
                    id=str(uuid.uuid4()),
                    project_id=state.project_id,
                    agent_name=self.name,
                    action_type="VALIDATION_FAILED",
                    timestamp=datetime.utcnow(),
                    input_parameters=input_params,
                    output_result="Code validation checks failed.",
                    explanation=explanation
                )
                state.audit_logs.append(log_entry)
                raise ValueError(f"Validation failed: {report.explanation}")

        except ValueError as err:
            # Re-raise validation failure already logged
            raise err
        except Exception as err:
            if state.status != ExcavationStatus.FAILED:
                state.status = ExcavationStatus.FAILED
                state.updated_at = datetime.utcnow()
                
            error_message = f"{type(err).__name__}: {str(err)}"
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="VALIDATION_ERROR",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=error_message,
                explanation=f"Validation execution encountered an unhandled error: {error_message}"
            )
            state.audit_logs.append(log_entry)
            raise err
