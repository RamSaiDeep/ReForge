import uuid
from datetime import datetime
from typing import List
from reforge.domain.interfaces import ArchaeologyAgent, RestorationExecutor
from reforge.domain.models import AgentLog, ExcavationState, ExcavationStatus

class RestorerAgent(ArchaeologyAgent):
    """The agent responsible for Stage 6 — Restoration.

    Runs the approved restoration plan steps to bring the legacy codebase into a working state.
    """

    def __init__(self, executor: RestorationExecutor) -> None:
        self.executor = executor

    @property
    def name(self) -> str:
        return "Restorer Agent"

    async def run(self, state: ExcavationState) -> List[str]:
        if not state.local_path:
            raise ValueError("ExcavationState must contain local_path to execute restoration.")
        if not state.restoration_plan:
            raise ValueError("ExcavationState must contain an approved restoration_plan to execute restoration.")

        state.status = ExcavationStatus.RESTORING
        state.updated_at = datetime.utcnow()

        input_params = {
            "project_id": state.project_id,
            "local_path": state.local_path,
            "steps_count": str(len(state.restoration_plan.steps))
        }

        try:
            # Execute restoration steps
            logs = await self.executor.execute(state.local_path, state.restoration_plan)
            
            # Transition status
            state.status = ExcavationStatus.RESTORED
            state.updated_at = datetime.utcnow()

            # Record Log
            explanation = f"Successfully completed Stage 6 Restoration in workspace. Executed {len(state.restoration_plan.steps)} migration/restoration steps."
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="RESTORATION_EXECUTION",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result="\n".join(logs),
                explanation=explanation
            )
            state.audit_logs.append(log_entry)
            return logs

        except Exception as err:
            state.status = ExcavationStatus.FAILED
            state.updated_at = datetime.utcnow()
            error_message = f"{type(err).__name__}: {str(err)}"
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="RESTORATION_EXECUTION_FAILED",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=error_message,
                explanation=f"Restoration execution failed during step command runs. Error: {error_message}"
            )
            state.audit_logs.append(log_entry)
            raise err
