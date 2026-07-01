import os
from typing import List
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, Field
from reforge.adapters.repositories import JSONFileProjectRepository
from reforge.adapters.github_provider import GitHubProvider
from reforge.adapters.git_cloner import LocalGitCloner
from reforge.adapters.workspace_inspector import LocalWorkspaceInspector
from reforge.domain.interfaces import ProjectRepository
from reforge.domain.models import ExcavationState
from reforge.usecases.scout import ScoutAgent
from reforge.usecases.heritage import HeritageEvaluator
from reforge.usecases.explorer import ExplorerAgent
from reforge.usecases.architect import ArchitectAgent
from reforge.adapters.code_analyzer import LocalCodeAnalyzer

# FastAPI initialization
app = FastAPI(
    title="ReForge Software Archaeology API",
    description="REST API for discovering, scoring, and understanding software heritage projects.",
    version="0.1.0"
)

# Global instances (blackboard adapters & drivers)
# Default to standard project storage folder
STORAGE_DIR = os.getenv("REFORGE_STORAGE_DIR", ".reforge_data")
repository = JSONFileProjectRepository(storage_dir=STORAGE_DIR)
git_provider = GitHubProvider()
git_cloner = LocalGitCloner()
workspace_inspector = LocalWorkspaceInspector()
code_analyzer = LocalCodeAnalyzer()

# Agents
scout_agent = ScoutAgent(git_provider=git_provider)
heritage_evaluator = HeritageEvaluator()
explorer_agent = ExplorerAgent(cloner=git_cloner, inspector=workspace_inspector)
architect_agent = ArchitectAgent(analyzer=code_analyzer)

# Supervisor
supervisor_workflow = SupervisorWorkflow(
    repository=repository,
    scout_agent=scout_agent,
    heritage_evaluator=heritage_evaluator,
    explorer_agent=explorer_agent,
    architect_agent=architect_agent
)



# Dependency Injection Helpers
def get_supervisor() -> SupervisorWorkflow:
    return supervisor_workflow

def get_repository() -> ProjectRepository:
    return repository


# DTO Request/Response Schemas
class ProjectCreateRequest(BaseModel):
    project_id: str = Field(..., min_length=3, max_length=50, description="Unique alphanumeric identifier")
    repository_url: str = Field(..., description="HTTPS URL of the Git repository")

class ExcavateRequest(BaseModel):
    force_continue: bool = Field(default=False, description="Continue past Stage 2 even if heritage score is low")


# API Routes
@app.post(
    "/projects",
    response_model=ExcavationState,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize an excavation project",
)
async def create_project(
    req: ProjectCreateRequest,
    supervisor: SupervisorWorkflow = Depends(get_supervisor)
):
    try:
        state = await supervisor.create_project(
            project_id=req.project_id,
            repository_url=req.repository_url
        )
        return state
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@app.post(
    "/projects/{project_id}/excavate",
    response_model=ExcavationState,
    summary="Run excavation pipeline stages",
)
async def excavate_project(
    project_id: str,
    req: ExcavateRequest = ExcavateRequest(),
    supervisor: SupervisorWorkflow = Depends(get_supervisor)
):
    try:
        state = await supervisor.execute_excavation(
            project_id=project_id,
            force_continue=req.force_continue
        )
        return state
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Excavation pipeline failure: {str(err)}"
        )


@app.get(
    "/projects/{project_id}",
    response_model=ExcavationState,
    summary="Retrieve excavation state details",
)
async def get_project(
    project_id: str,
    repo: ProjectRepository = Depends(get_repository)
):
    state = await repo.get_by_id(project_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )
    return state


@app.get(
    "/projects",
    response_model=List[ExcavationState],
    summary="List all excavation projects",
)
async def list_projects(
    repo: ProjectRepository = Depends(get_repository)
):
    return await repo.list_projects()
