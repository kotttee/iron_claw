import json
from pathlib import Path
from typing import List, Dict, Any

# --- File Naming Standard ---
LOGS_DIR = Path("data/logs")
HISTORY_PATH = LOGS_DIR / "history.jsonl"

class MemoryManager:
    """
    Handles all memory operations, including short-term context and long-term logging.
    """
    def __init__(self, rolling_window_size: int = 10):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.rolling_window_size = rolling_window_size

    def log_interaction(self, role: str, content: str):
        """
        Appends a single interaction to the raw history log (history.jsonl).

        Args:
            role: The role of the speaker (e.g., 'user', 'assistant', 'tool').
            content: The message or data content.
        """
        log_entry = {"role": role, "content": content}
        try:
            with open(HISTORY_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except IOError as e:
            print(f"Error logging interaction to {HISTORY_PATH}: {e}")

    def get_rolling_context(self) -> List[Dict[str, Any]]:
        """
        Retrieves the last N messages from the history log to serve as short-term memory.

        Returns:
            A list of message dictionaries, ready to be injected into an LLM prompt.
        """
        if not HISTORY_PATH.exists():
            return []

        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Take the last N lines for the rolling window
            last_n_lines = lines[-self.rolling_window_size:]
            
            context = []
            for line in last_n_lines:
                try:
                    context.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip corrupted lines
                    continue
            return context
        except IOError as e:
            print(f"Error reading rolling context from {HISTORY_PATH}: {e}")
            return []
