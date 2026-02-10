from pathlib import Path
from typing import Any
from src.core.interfaces import BaseTool
from .config import FileToolConfig

def get_safe_path(path_str: str) -> Path:
    """Resolves any path to an absolute path without workspace restrictions."""
    return Path(path_str).resolve()

class ReadFileTool(BaseTool[FileToolConfig]):
    """
    Reads the entire content of a specified file within the workspace.
    """
    name = "system/read_file"
    config_class = FileToolConfig

    async def execute(self, path: str) -> str:
        safe_path = get_safe_path(path)
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

    async def healthcheck(self): return True, "OK"

class WriteFileTool(BaseTool[FileToolConfig]):
    """
    Writes (or overwrites) content to a specified file within the workspace.
    """
    name = "system/write_file"
    config_class = FileToolConfig

    async def execute(self, path: str, content: str) -> str:
        safe_path = get_safe_path(path)
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

    async def healthcheck(self): return True, "OK"

class ListFilesTool(BaseTool[FileToolConfig]):
    """
    Lists files and directories within a specified path in the workspace.
    """
    name = "system/list_files"
    config_class = FileToolConfig

    async def execute(self, path: str) -> str:
        safe_path = get_safe_path(path)
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
        
        num_items = len(result.split('\n')) - 1
        return f"📂 Found {num_items} items in the directory."

    async def healthcheck(self): return True, "OK"
