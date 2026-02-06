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
                # Attempt to read and parse the file
                with HISTORY_PATH.open("r", encoding="utf-8") as f:
                    content = f.read()
                    if not content:
                        return "History is empty."
                    history_data = json.loads(content)
                
                # If parsing is successful, proceed with the search
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
                
                # If search is complete, return the result and exit the function
                return "Found the following occurrences in history:\n" + "\n".join(found_messages)

            except json.JSONDecodeError:
                # If JSON is invalid, it might be a race condition. Wait and retry.
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    # If all retries fail, return an error
                    return "Error: Could not decode history file after multiple attempts. It might be corrupt or in use."
            except Exception as e:
                # For any other exception, fail immediately
                return f"An unexpected error occurred while reading history: {e}"
        
        # This line should not be reachable given the logic above.
        return "An unknown error occurred in the search tool."
