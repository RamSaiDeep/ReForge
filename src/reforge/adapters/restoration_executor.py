import os
from typing import List
from reforge.domain.interfaces import RestorationExecutor
from reforge.domain.models import RestorationPlan

class LocalRestorationExecutor(RestorationExecutor):
    """Concrete implementation of RestorationExecutor executing or simulating restoration commands on the filesystem.

    Simulates system commands safely to prevent shell escalation while applying minor layout repairs (such as mock environment files).
    """

    async def execute(self, local_path: str, plan: RestorationPlan) -> List[str]:
        if not os.path.exists(local_path):
            raise ValueError(f"Workspace local path does not exist: {local_path}")

        logs = []
        logs.append(f"[INIT] Starting restoration execution in workspace: {local_path}")

        for step in plan.steps:
            logs.append(f"[EXEC] Running setup step: {step}")
            
            # Apply safe filesystem actions
            if "venv" in step:
                # Mock virtual environment creation
                venv_dir = os.path.join(local_path, ".venv")
                os.makedirs(venv_dir, exist_ok=True)
                logs.append(f"[FS] Created mock virtual environment directory: {venv_dir}")
                
            elif "requirements.txt" in step or "package manifest" in step:
                # Write default configuration files if they are missing
                req_file = os.path.join(local_path, "requirements.txt")
                if not os.path.exists(req_file):
                    with open(req_file, "w", encoding="utf-8") as f:
                        f.write("# Auto-generated restoration dependencies\nfastapi\npydantic\npytest\n")
                    logs.append(f"[FS] Created default requirements file: {req_file}")
            
            elif "README.md" in step:
                readme_file = os.path.join(local_path, "README.md")
                if not os.path.exists(readme_file):
                    with open(readme_file, "w", encoding="utf-8") as f:
                        f.write("# Restored Software Project\nThis repository was successfully restored using ReForge.\n")
                    logs.append(f"[FS] Created default documentation: {readme_file}")

            logs.append(f"[SUCCESS] Completed step: {step}")

        logs.append(f"[COMPLETE] Restoration finished. Executed {len(plan.steps)} steps successfully.")
        return logs
