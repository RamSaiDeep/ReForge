import uuid
from datetime import datetime
from pydantic import BaseModel
from reforge.domain.interfaces import ArchaeologyAgent, GitProvider
from reforge.domain.models import AgentLog, ExcavationState, ExcavationStatus, RepositoryProfile

class ScoutAgent(ArchaeologyAgent):
    """The agent responsible for Stage 1 — Repository Discovery.

    It fetches initial metadata from the Git provider and saves it in the shared state.
    """

    def __init__(self, git_provider: GitProvider) -> None:
        self.git_provider = git_provider

    @property
    def name(self) -> str:
        return "Repository Scout"

    async def run(self, state: ExcavationState) -> RepositoryProfile:
        """Fetch metadata, update state, and log the action.

        Args:
            state: The current global excavation state.

        Returns:
            The discovered RepositoryProfile.
        """
        # Transition state to DISCOVERING
        state.status = ExcavationStatus.DISCOVERING
        state.updated_at = datetime.utcnow()
        
        start_time = datetime.utcnow()
        input_params = {
            "repository_url": state.repository_url,
            "project_id": state.project_id
        }

        try:
            # Fetch repository profile metadata
            profile = await self.git_provider.fetch_profile(state.repository_url)
            
            # Update state with retrieved profile
            state.profile = profile
            state.status = ExcavationStatus.DISCOVERED
            state.updated_at = datetime.utcnow()
            
            # Log success
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="METADATA_FETCH",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=profile.model_dump_json(indent=2),
                explanation=(
                    f"Successfully scouted repository. Discovered project '{profile.name}' "
                    f"owned by '{profile.owner}'. Found {profile.stars} stars and "
                    f"identified primary language as '{profile.primary_language}'."
                )
            )
            state.audit_logs.append(log_entry)
            return profile

        except Exception as err:
            # Transition state to FAILED
            state.status = ExcavationStatus.FAILED
            state.updated_at = datetime.utcnow()
            
            # Log failure
            error_message = f"{type(err).__name__}: {str(err)}"
            log_entry = AgentLog(
                id=str(uuid.uuid4()),
                project_id=state.project_id,
                agent_name=self.name,
                action_type="METADATA_FETCH_FAILED",
                timestamp=datetime.utcnow(),
                input_parameters=input_params,
                output_result=error_message,
                explanation=f"Discovery failed while scouting repository. Error: {error_message}"
            )
            state.audit_logs.append(log_entry)
            raise err
