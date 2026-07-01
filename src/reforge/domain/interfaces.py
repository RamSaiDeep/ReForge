from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from reforge.domain.models import ExcavationState, RepositoryProfile

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
