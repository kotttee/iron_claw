import json
from pathlib import Path
from typing import Type, List

from pydantic import BaseModel, Field

from src.interfaces.tool import BaseTool

# --- File Naming Standard ---
LOGS_DIR = Path("data/logs")
HISTORY_PATH = LOGS_DIR / "history.json"

class SearchHistoryTool(BaseTool):
    """A tool to search the raw interaction history log."""
    @property
    def name(self) -> str:
        return "memory/search_history"
    @property
    def description(self) -> str:
        return "Searches the complete, raw conversation history log (history.jsonl) for an exact query. Useful for recalling specific past interactions."
    @property
    def args_schema(self) -> Type[BaseModel]:
        class SearchHistoryArgs(BaseModel):
            query: str = Field(..., description="The exact text string to search for in the history.")
        return SearchHistoryArgs

    def execute(self, query: str) -> str:
        """Searches for a query in the history.jsonl file."""
        if not HISTORY_PATH.exists():
            return "History log not found."

        found_lines: List[str] = []
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if query in line:
                        try:
                            # Format for better readability
                            log_entry = json.loads(line)
                            found_lines.append(f"[{log_entry.get('role', 'unknown')}]: {log_entry.get('content', '')}")
                        except json.JSONDecodeError:
                            continue
            
            if not found_lines:
                return f"No occurrences of '{query}' found in history."
            
            return "Found the following occurrences in history:\n" + "\n".join(found_lines)
        except Exception as e:
            return f"Error searching history: {e}"
