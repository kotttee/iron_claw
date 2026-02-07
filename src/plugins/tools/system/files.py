from pathlib import Path
from typing import Type

from pydantic import BaseModel, Field

from src.interfaces.tool import BaseTool

WORKSPACE_DIR = Path("data/workspace")
WORKSPACE_DIR.mkdir(exist_ok=True, parents=True)

class SafePathArgs(BaseModel):
    path: str = Field(..., description="The relative path to the file or directory within the workspace.")

def get_safe_path(relative_path: str) -> Path | None:
    safe_path = (WORKSPACE_DIR / relative_path).resolve()
    if WORKSPACE_DIR.resolve() in safe_path.parents or safe_path == WORKSPACE_DIR.resolve():
        return safe_path
    return None

class ReadFileTool(BaseTool):
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
            return f"Error: Path '{path}' is not a file or does not exist."
        try:
            return safe_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

    def format_output(self, result: str) -> str:
        if result.startswith("Error"):
            return f"⚠️ {result}"
        return f"✅ Read {len(result)} characters from the file."

class WriteFileTool(BaseTool):
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
            bytes_written = safe_path.write_text(content, encoding="utf-8")
            return f"Successfully wrote {bytes_written} bytes to '{path}'."
        except Exception as e:
            return f"Error writing file: {e}"

    def format_output(self, result: str) -> str:
        if result.startswith("Error"):
            return f"⚠️ {result}"
        return f"📝 {result}"

class ListFilesTool(BaseTool):
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
            return f"Error: Path '{path}' is not a directory or does not exist."
        try:
            entries = [f.name for f in safe_path.iterdir()]
            if not entries:
                return "Directory is empty."
            return "Directory listing:\n- " + "\n- ".join(entries)
        except Exception as e:
            return f"Error listing files: {e}"

    def format_output(self, result: str) -> str:
        if result.startswith("Error"):
            return f"⚠️ {result}"
        if result == "Directory is empty.":
            return "📂 Directory is empty."
        
        num_items = len(result.split('\n')) -1
        return f"📂 Found {num_items} items in the directory."
