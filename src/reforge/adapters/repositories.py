import copy
import json
import os
from typing import Dict, List, Optional
from reforge.domain.interfaces import ProjectRepository
from reforge.domain.models import ExcavationState

class InMemoryProjectRepository(ProjectRepository):
    """An in-memory implementation of ProjectRepository, perfect for testing and prototyping."""

    def __init__(self) -> None:
        self._projects: Dict[str, ExcavationState] = {}

    async def get_by_id(self, project_id: str) -> Optional[ExcavationState]:
        state = self._projects.get(project_id)
        if state:
            # Return a copy to mimic database isolation
            return copy.deepcopy(state)
        return None

    async def save(self, state: ExcavationState) -> None:
        # Save a copy to mimic database isolation
        self._projects[state.project_id] = copy.deepcopy(state)

    async def list_projects(self) -> List[ExcavationState]:
        return [
            copy.deepcopy(state) 
            for state in self._projects.values()
        ]



class JSONFileProjectRepository(ProjectRepository):
    """A local file-based implementation of ProjectRepository, storing project state as JSON files."""

    def __init__(self, storage_dir: str = ".reforge_data") -> None:
        self.storage_dir = storage_dir
        # Ensure the directory exists
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_file_path(self, project_id: str) -> str:
        # Sanitize project_id to prevent directory traversal
        safe_id = "".join(c for c in project_id if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.storage_dir, f"{safe_id}.json")

    async def get_by_id(self, project_id: str) -> Optional[ExcavationState]:
        file_path = self._get_file_path(project_id)
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_json = f.read()
                return ExcavationState.model_validate_json(raw_json)
        except (json.JSONDecodeError, ValueError):
            # If corruption or format mismatch occurs, handle gracefully
            return None

    async def save(self, state: ExcavationState) -> None:
        file_path = self._get_file_path(state.project_id)
        # Serialize to JSON with formatting for readability (software archaeology friendly!)
        serialized = state.model_dump_json(indent=2)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(serialized)

    async def list_projects(self) -> List[ExcavationState]:
        states: List[ExcavationState] = []
        if not os.path.exists(self.storage_dir):
            return states
            
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                project_id = filename[:-5]
                state = await self.get_by_id(project_id)
                if state:
                    states.append(state)
        return states
