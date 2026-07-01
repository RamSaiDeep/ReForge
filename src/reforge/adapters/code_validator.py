import os
import py_compile
from reforge.domain.interfaces import CodeValidator

class LocalCodeValidator(CodeValidator):
    """Concrete implementation of CodeValidator.

    Traverses python files and runs compilation checks to verify syntactic correctness.
    """

    def __init__(self) -> None:
        self.exclude_dirs = {".git", ".venv", "node_modules", "__pycache__"}

    async def validate(self, local_path: str) -> bool:
        if not os.path.exists(local_path):
            raise ValueError(f"Target path does not exist for validation: {local_path}")

        try:
            for root, dirs, files in os.walk(local_path):
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        try:
                            # Run native syntax check compilation
                            py_compile.compile(file_path, doraise=True)
                        except py_compile.PyCompileError:
                            # Compilation / syntax error identified
                            return False
            return True
        except Exception:
            return False
