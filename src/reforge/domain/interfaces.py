from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from reforge.domain.models import ExcavationState, RepositoryProfile, SoftwareOverview, ArchitectureReport, RestorationPlan

class CodeValidator(ABC):
    """Abstract interface for running validation or syntax compilations on a codebase."""

    @abstractmethod
    async def validate(self, local_path: str) -> bool:
        """Scan codebase files and run compilation/validation checks.

        Args:
            local_path: The local filesystem path of the repository workspace.

        Returns:
            True if codebase compiles successfully without syntax errors, False otherwise.
        """
        pass


class RestorationExecutor(ABC):
    """Abstract interface for executing approved restoration plan steps on a codebase workspace."""

    @abstractmethod
    async def execute(self, local_path: str, plan: RestorationPlan) -> List[str]:
        """Execute the migration/restoration instructions and return log outputs.

        Args:
            local_path: The local filesystem path of the repository workspace.
            plan: The approved RestorationPlan containing issues and setup steps.

        Returns:
            A list of execution output strings/logs.
        """
        pass


class CodeAnalyzer(ABC):
    """Abstract interface for analyzing codebases and reconstructing their internal architecture."""

    @abstractmethod
    async def analyze(self, local_path: str) -> ArchitectureReport:
        """Parse source files to map module structure, imports, components, and relationships.

        Args:
            local_path: The local filesystem path of the repository workspace.

        Returns:
            A populated ArchitectureReport domain model.
        """
        pass


class GitCloner(ABC):
    """Abstract interface for cloning remote repositories."""

    @abstractmethod
    async def clone(self, repo_url: str, dest_path: str) -> None:
        """Clone a remote git repository to a local filesystem path.

        Args:
            repo_url: The HTTPS URL of the Git repository.
            dest_path: The local directory path where the codebase will be cloned.
        """
        pass


class WorkspaceInspector(ABC):
    """Abstract interface for crawling and inspecting a cloned codebase directory."""

    @abstractmethod
    async def inspect(self, local_path: str) -> SoftwareOverview:
        """Parse files, configurations, and folders to generate a SoftwareOverview.

        Args:
            local_path: The local filesystem path to inspect.

        Returns:
            A populated SoftwareOverview domain model.
        """
        pass


class GitProvider(ABC):
    """Abstract interface for interacting with Git hosting platforms (e.g. GitHub)."""

    @abstractmethod
    async def fetch_profile(self, repo_url: str) -> RepositoryProfile:
        """Fetch metadata for a remote repository and construct its profile.

        Args:
            repo_url: The full Git repository HTTP/HTTPS URL.

        Returns:
            A populated RepositoryProfile entity.

        Raises:
            ValueError: If the repository URL is invalid or malformed.
            Exception: If fetching from the provider API fails.
        """
        pass


class ProjectRepository(ABC):
    """Abstract interface for managing project excavation state persistence."""

    @abstractmethod
    async def get_by_id(self, project_id: str) -> Optional[ExcavationState]:
        """Retrieve an excavation project state by its unique ID."""
        pass

    @abstractmethod
    async def save(self, state: ExcavationState) -> None:
        """Persist or update the excavation project state."""
        pass

    @abstractmethod
    async def list_projects(self) -> List[ExcavationState]:
        """List all current excavation projects."""
        pass


class ArchaeologyAgent(ABC):
    """Abstract base class representing an autonomous software archaeology agent."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the agent."""
        pass

    @abstractmethod
    async def run(self, state: ExcavationState) -> BaseModel:
        """Execute the agent's core task on the excavation state.

        Args:
            state: The current global blackboard state of the project.

        Returns:
            A strongly-typed Pydantic model representing the result contract.
        """
        pass
