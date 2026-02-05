from pathlib import Path
from typing import Type

from pydantic import BaseModel, Field

from src.interfaces.tool import BaseTool

# For security, tools should only operate within a designated workspace.
WORKSPACE_DIR = Path("data/workspace")
WORKSPACE_DIR.mkdir(exist_ok=True, parents=True)

class SafePathArgs(BaseModel):
    path: str = Field(..., description="The relative path to the file or directory within the workspace.")

def get_safe_path(relative_path: str) -> Path | None:
    """Resolves a relative path to an absolute path, ensuring it's within the workspace."""
    safe_path = (WORKSPACE_DIR / relative_path).resolve()
    if WORKSPACE_DIR.resolve() in safe_path.parents or safe_path == WORKSPACE_DIR.resolve():
        return safe_path
    return None

class ReadFileTool(BaseTool):
    """A tool to read the content of a file within the designated workspace."""
    @property
    def name(self) -> str:
        return "system/read_file"
    @property
    def description(self) -> str:
        return "Reads the entire content of a specified file within the workspace."
    @property
    def args_schema(self) -> Type[BaseModel]:
        return SafePathArgs

    def execute(self, path: str) -> str:
        safe_path = get_safe_path(path)
        if not safe_path:
            return f"Error: Access denied. Path is outside the allowed workspace."
        if not safe_path.is_file():
            return f"Error: Path '{path}' is not a file."
        try:
            return safe_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

class WriteFileTool(BaseTool):
    """A tool to write content to a file within the designated workspace."""
    @property
    def name(self) -> str:
        return "system/write_file"
    @property
    def description(self) -> str:
        return "Writes (or overwrites) content to a specified file within the workspace."
    @property
    def args_schema(self) -> Type[BaseModel]:
        class WriteFileArgs(SafePathArgs):
            content: str = Field(..., description="The content to write to the file.")
        return WriteFileArgs

    def execute(self, path: str, content: str) -> str:
        safe_path = get_safe_path(path)
        if not safe_path:
            return f"Error: Access denied. Path is outside the allowed workspace."
        try:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(content, encoding="utf-8")
            return f"Successfully wrote to '{path}'."
        except Exception as e:
            return f"Error writing file: {e}"

class ListFilesTool(BaseTool):
    """A tool to list files and directories within a specified path in the workspace."""
    @property
    def name(self) -> str:
        return "system/list_files"
    @property
    def description(self) -> str:
        return "Lists files and directories within a specified path in the workspace."
    @property
    def args_schema(self) -> Type[BaseModel]:
        return SafePathArgs

    def execute(self, path: str) -> str:
        safe_path = get_safe_path(path)
        if not safe_path:
            return f"Error: Access denied. Path is outside the allowed workspace."
        if not safe_path.is_dir():
            return f"Error: Path '{path}' is not a directory."
        try:
            entries = [f.name for f in safe_path.iterdir()]
            return "Directory listing:\n- " + "\n- ".join(entries) if entries else "Directory is empty."
        except Exception as e:
            return f"Error listing files: {e}"
