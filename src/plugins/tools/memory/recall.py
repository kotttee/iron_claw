import json
import time
from typing import Type, List

from pydantic import BaseModel, Field

from src.interfaces.tool import BaseTool
from src.core.paths import HISTORY_PATH

class SearchHistoryTool(BaseTool):
    """A tool to search the raw interaction history log."""

    @property
    def name(self) -> str:
        return "memory/search_history"

    @property
    def description(self) -> str:
        return "Searches the complete, raw conversation history log (history.json) for a query. Useful for recalling specific past interactions."

    @property
    def args_schema(self) -> Type[BaseModel]:
        class SearchHistoryArgs(BaseModel):
            query: str = Field(..., description="The text string to search for in the history.")
        return SearchHistoryArgs

    def execute(self, query: str) -> str:
        """Searches for a query in the history.json file with a retry mechanism."""
        if not HISTORY_PATH.exists():
            return "History file does not exist."

        max_retries = 5
        retry_delay = 0.5  # seconds

        for attempt in range(max_retries):
            try:
                with HISTORY_PATH.open("r", encoding="utf-8") as f:
                    content = f.read()
                    if not content:
                        return "History is empty."
                    history_data = json.loads(content)
                
                if not isinstance(history_data, list):
                    return "Error: History data is not in the expected list format."

                found_messages: List[str] = []
                lower_query = query.lower()

                for entry in history_data:
                    if isinstance(entry, dict):
                        content = entry.get('content', '')
                        if content and lower_query in str(content).lower():
                            role = entry.get('role', 'unknown')
                            found_messages.append(f"[{role}]: {content}")
                
                if not found_messages:
                    return f"No occurrences of '{query}' found in history."
                
                return "Found the following occurrences in history:\n" + "\n".join(found_messages)

            except json.JSONDecodeError:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    return "Error: Could not decode history file after multiple attempts. It might be corrupt or in use."
            except Exception as e:
                return f"An unexpected error occurred while reading history: {e}"
        
        return "An unknown error occurred in the search tool."

    def format_output(self, result: str) -> str:
        """Formats the history search result for user-facing output."""
        if result.startswith("Error") or "does not exist" in result or "is empty" in result:
            return f"⚠️ {result}"
        
        if result.startswith("No occurrences"):
            return f"🤷 {result}"
            
        num_found = len(result.split('\n')) - 1
        return f"🔎 Found {num_found} relevant messages in the conversation history."
