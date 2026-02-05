from pathlib import Path
from typing import Type

from pydantic import BaseModel, Field

from src.interfaces.tool import BaseTool

# --- File Naming Standard ---
MEMORY_DIR = Path("data/memory")
NOTEBOOK_PATH = MEMORY_DIR / "memory.md"

def _ensure_file_exists():
    """Private helper to ensure the memory file and directory exist."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not NOTEBOOK_PATH.exists():
        NOTEBOOK_PATH.touch()

class ReadMemoryTool(BaseTool):
    """A tool to read the agent's long-term memory notebook."""
    @property
    def name(self) -> str:
        return "memory/read_notebook"
    @property
    def description(self) -> str:
        return "Reads the entire content of your long-term memory notebook (memory.md)."
    @property
    def args_schema(self) -> Type[BaseModel]:
        return BaseModel  # No arguments needed

    def execute(self) -> str:
        _ensure_file_exists()
        try:
            return NOTEBOOK_PATH.read_text(encoding="utf-8") or "The memory notebook is currently empty."
        except Exception as e:
            return f"Error reading memory notebook: {e}"

class WriteMemoryTool(BaseTool):
    """A tool to append text to the agent's long-term memory notebook."""
    @property
    def name(self) -> str:
        return "memory/write_notebook"
    @property
    def description(self) -> str:
        return "Appends a new entry to your long-term memory notebook (memory.md). Use this to store important, non-transient information."
    @property
    def args_schema(self) -> Type[BaseModel]:
        class WriteMemoryArgs(BaseModel):
            text: str = Field(..., description="The text to append to the memory notebook. Should be formatted in Markdown.")
        return WriteMemoryArgs

    def execute(self, text: str) -> str:
        _ensure_file_exists()
        try:
            with open(NOTEBOOK_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n\n---\n\n{text}")
            return "Successfully appended text to the memory notebook."
        except Exception as e:
            return f"Error writing to memory notebook: {e}"
