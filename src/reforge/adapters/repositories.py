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
        self._history: Dict[str, List[ExcavationState]] = {}

    async def get_by_id(self, project_id: str) -> Optional[ExcavationState]:
        state = self._projects.get(project_id)
        if state:
            return copy.deepcopy(state)
        return None

    async def save(self, state: ExcavationState) -> None:
        copied = copy.deepcopy(state)
        self._projects[state.project_id] = copied
        if state.project_id not in self._history:
            self._history[state.project_id] = []
        self._history[state.project_id].append(copied)

    async def list_projects(self) -> List[ExcavationState]:
        return [
            copy.deepcopy(state) 
            for state in self._projects.values()
        ]

    async def get_project_history(self, project_id: str) -> List[ExcavationState]:
        history = self._history.get(project_id, [])
        # Return sorted by updated_at
        sorted_history = sorted(history, key=lambda s: s.updated_at)
        return [copy.deepcopy(s) for s in sorted_history]


class JSONFileProjectRepository(ProjectRepository):
    """A local file-based implementation of ProjectRepository, storing project state as JSON files."""

    def __init__(self, storage_dir: str = ".reforge_data") -> None:
        self.storage_dir = storage_dir
        # Ensure the directory exists
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_file_path(self, project_id: str) -> str:
        safe_id = "".join(c for c in project_id if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.storage_dir, f"{safe_id}.json")

    def _get_run_file_path(self, project_id: str, timestamp_str: str) -> str:
        safe_id = "".join(c for c in project_id if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.storage_dir, f"{safe_id}#run-{timestamp_str}.json")

    async def get_by_id(self, project_id: str) -> Optional[ExcavationState]:
        file_path = self._get_file_path(project_id)
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_json = f.read()
                return ExcavationState.model_validate_json(raw_json)
        except (json.JSONDecodeError, ValueError):
            return None

    async def save(self, state: ExcavationState) -> None:
        # Save standard reference file
        file_path = self._get_file_path(state.project_id)
        serialized = state.model_dump_json(indent=2)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(serialized)

        # Save historical snapshot run file
        timestamp_str = state.updated_at.strftime("%Y%m%d%H%M%S")
        run_file_path = self._get_run_file_path(state.project_id, timestamp_str)
        with open(run_file_path, "w", encoding="utf-8") as f:
            f.write(serialized)

    async def list_projects(self) -> List[ExcavationState]:
        states: List[ExcavationState] = []
        if not os.path.exists(self.storage_dir):
            return states
            
        for filename in os.listdir(self.storage_dir):
            # Only read non-run index files to list projects
            if filename.endswith(".json") and "#run-" not in filename:
                project_id = filename[:-5]
                state = await self.get_by_id(project_id)
                if state:
                    states.append(state)
        return states

    async def get_project_history(self, project_id: str) -> List[ExcavationState]:
        states: List[ExcavationState] = []
        if not os.path.exists(self.storage_dir):
            return states

        safe_id = "".join(c for c in project_id if c.isalnum() or c in ("-", "_"))
        prefix = f"{safe_id}#run-"

        for filename in os.listdir(self.storage_dir):
            if filename.startswith(prefix) and filename.endswith(".json"):
                file_path = os.path.join(self.storage_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        raw_json = f.read()
                        state = ExcavationState.model_validate_json(raw_json)
                        states.append(state)
                except Exception:
                    pass

        # Return sorted by updated_at
        return sorted(states, key=lambda s: s.updated_at)
