from typing import Type

from pydantic import BaseModel, Field

from src.interfaces.tool import BaseTool
from src.core.paths import MEMORY_DIR

NOTEBOOK_PATH = MEMORY_DIR / "memory.md"

def _ensure_file_exists():
    MEMORY_DIR.mkdir(exist_ok=True, parents=True)
    if not NOTEBOOK_PATH.exists():
        NOTEBOOK_PATH.touch()

class ReadMemoryTool(BaseTool):
    @property
    def name(self) -> str:
        return "memory/read_notebook"
    @property
    def description(self) -> str:
        return "Reads the entire content of your long-term memory notebook (memory.md)."
    @property
    def args_schema(self) -> Type[BaseModel]:
        return BaseModel

    def execute(self) -> str:
        _ensure_file_exists()
        try:
            content = NOTEBOOK_PATH.read_text(encoding="utf-8")
            return content or "The memory notebook is currently empty."
        except Exception as e:
            return f"Error reading memory notebook: {e}"

    def format_output(self, result: str) -> str:
        if result.startswith("Error"):
            return f"⚠️ {result}"
        if result == "The memory notebook is currently empty.":
            return "🧠 The memory notebook is empty."
        return f"🧠 Read {len(result)} characters from the memory notebook."

class WriteMemoryTool(BaseTool):
    @property
    def name(self) -> str:
        return "memory/write_notebook"
    @property
    def description(self) -> str:
        return "Appends a new entry to your long-term memory notebook (memory.md)."
    @property
    def args_schema(self) -> Type[BaseModel]:
        class WriteMemoryArgs(BaseModel):
            text: str = Field(..., description="The text to append to the memory notebook.")
        return WriteMemoryArgs

    def execute(self, text: str) -> str:
        _ensure_file_exists()
        try:
            with open(NOTEBOOK_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n\n---\n\n{text}")
            return f"Successfully appended {len(text)} characters to the memory notebook."
        except Exception as e:
            return f"Error writing to memory notebook: {e}"

    def format_output(self, result: str) -> str:
        if result.startswith("Error"):
            return f"⚠️ {result}"
        return f"💾 {result}"
