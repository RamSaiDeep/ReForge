import os
import uuid
from datetime import datetime
from reforge.domain.interfaces import ArchaeologyAgent, GitCloner, WorkspaceInspector
from reforge.domain.models import AgentLog, ExcavationState, ExcavationStatus, SoftwareOverview

class ExplorerAgent(ArchaeologyAgent):
    """The agent responsible for Stage 3 — Software Understanding.

    Clones the repository locally and inspects its structure and dependencies.
    """

    def __init__(
        self,
        cloner: GitCloner,
        inspector: WorkspaceInspector,
        storage_base_dir: str = ".reforge_workspaces"
    ) -> None:
        self.cloner = cloner
        self.inspector = inspector
        self.storage_base_dir = storage_base_dir

    @property
    def name(self) -> str:
        return "Repository Explorer"

    async def run(self, state: ExcavationState) -> SoftwareOverview:
        state.status = ExcavationStatus.UNDERSTANDING
        state.updated_at = datetime.utcnow()

        dest_path = os.path.abspath(os.path.join(self.storage_base_dir, state.project_id))
        input_params = {
            "project_id": state.project_id,
            "repository_url": state.repository_url,
            "destination_path": dest_path
        }

        try:
            # 1. Clone the codebase locally
            await self.cloner.clone(state.repository_url, dest_path)
            state.local_path = dest_path
            
            # 2. Crawl and inspect the workspace
            overview = await self.inspector.inspect(dest_path)
            
            # 3. Update state
            state.software_overview = overview
            state.status = ExcavationStatus.UNDERSTOOD
            state.updated_at = datetime.utcnow()

            # 4. Log audit log
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="WORKSPACE_UNDERSTANDING",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=overview.model_dump_json(indent=2),
                explanation=overview.explanation
            )
            state.audit_logs.append(log_entry)
            return overview

        except Exception as err:
            state.status = ExcavationStatus.FAILED
            state.updated_at = datetime.utcnow()
            error_message = f"{type(err).__name__}: {str(err)}"
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="WORKSPACE_UNDERSTANDING_FAILED",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=error_message,
                explanation=f"Software understanding failed during workspace crawling. Error: {error_message}"
            )
            state.audit_logs.append(log_entry)
            raise err
