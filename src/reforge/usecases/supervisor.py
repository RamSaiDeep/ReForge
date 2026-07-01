from typing import Optional
from reforge.domain.interfaces import ProjectRepository
from reforge.domain.models import ExcavationState, ExcavationStatus
from reforge.usecases.scout import ScoutAgent
from reforge.usecases.heritage import HeritageEvaluator
from reforge.usecases.explorer import ExplorerAgent
from reforge.usecases.architect import ArchitectAgent

class SupervisorWorkflow:
    """The Supervisor coordinates all specialized agents and controls the excavation workflow state transitions.

    Following Clean Architecture, it coordinates usecase execution and persists progress.
    """

    def __init__(
        self,
        repository: ProjectRepository,
        scout_agent: ScoutAgent,
        heritage_evaluator: HeritageEvaluator,
        explorer_agent: ExplorerAgent,
        architect_agent: ArchitectAgent
    ) -> None:
        self.repository = repository
        self.scout_agent = scout_agent
        self.heritage_evaluator = heritage_evaluator
        self.explorer_agent = explorer_agent
        self.architect_agent = architect_agent

    async def create_project(self, project_id: str, repository_url: str) -> ExcavationState:
        """Initialize a new excavation project and save its initial state."""
        existing = await self.repository.get_by_id(project_id)
        if existing:
            raise ValueError(f"Project with ID '{project_id}' already exists.")

        state = ExcavationState(
            project_id=project_id,
            repository_url=repository_url,
            status=ExcavationStatus.PENDING
        )
        await self.repository.save(state)
        return state

    async def execute_excavation(self, project_id: str, force_continue: bool = False) -> ExcavationState:
        """Run the excavation pipeline sequentially through its available stages.

        Args:
            project_id: The ID of the excavation project to run.
            force_continue: Force continuation past the heritage evaluation checkpoint if score is low.

        Returns:
            The final updated ExcavationState.
        """
        state = await self.repository.get_by_id(project_id)
        if not state:
            raise ValueError(f"Project with ID '{project_id}' does not exist.")

        # Stage 1: Discovery (Scout Agent)
        if state.status in (ExcavationStatus.PENDING, ExcavationStatus.DISCOVERING, ExcavationStatus.FAILED):
            if not state.profile:
                try:
                    await self.scout_agent.run(state)
                except Exception:
                    # Scout agent has already updated status to FAILED and logged the error
                    await self.repository.save(state)
                    return state
                await self.repository.save(state)

        # Stage 2: Heritage Evaluation (Heritage Evaluator Agent)
        if state.status in (ExcavationStatus.DISCOVERED, ExcavationStatus.EVALUATING):
            try:
                await self.heritage_evaluator.run(state)
            except Exception:
                # Heritage evaluator has already updated status to FAILED and logged the error
                await self.repository.save(state)
                return state
                
            # If the evaluator stopped the excavation because it's not worth preserving
            if state.status == ExcavationStatus.STOPPED:
                if force_continue:
                    # User forces continuation, advance to EVALUATED state override
                    state.status = ExcavationStatus.EVALUATED
                else:
                    # Terminate analysis as specified by ReForge process
                    await self.repository.save(state)
                    return state
            
            await self.repository.save(state)

        # Stage 3: Software Understanding (Explorer Agent)
        if state.status in (ExcavationStatus.EVALUATED, ExcavationStatus.UNDERSTANDING):
            try:
                await self.explorer_agent.run(state)
            except Exception:
                # Explorer agent has already updated status to FAILED and logged the error
                await self.repository.save(state)
                return state
            await self.repository.save(state)

        # Stage 4: Architecture Reconstruction (Architect Agent)
        if state.status in (ExcavationStatus.UNDERSTOOD, ExcavationStatus.RECONSTRUCTING):
            try:
                await self.architect_agent.run(state)
            except Exception:
                # Architect agent has already updated status to FAILED and logged the error
                await self.repository.save(state)
                return state
            await self.repository.save(state)

        return state


