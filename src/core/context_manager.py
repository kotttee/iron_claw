import json
from pathlib import Path
from typing import List, Dict, Any

# Define paths relative to this file
DATA_ROOT = Path(__file__).parent.parent.parent / "data"
MEMORY_DIR = DATA_ROOT / "memory"
HISTORY_PATH = MEMORY_DIR / "short_term_history.json"
CONFIG_PATH = DATA_ROOT / "config.json"

class ContextManager:
    """
    Manages the shared short-term conversation history.
    It ensures that the context does not exceed a configurable limit and
    persists the history to a JSON file.
    """
    def __init__(self):
        """Initializes the ContextManager, loading configuration and history."""
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.max_history_limit = self._get_limit_from_config()
        self.history = self.load_context()

    def _get_limit_from_config(self) -> int:
        """Loads the history limit from the main config file."""
        try:
            if CONFIG_PATH.exists():
                config_data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                return int(config_data.get("max_history_limit", 20))
        except (json.JSONDecodeError, ValueError):
            pass # Fallback to default if file is corrupt or value is invalid
        return 20

    def load_context(self) -> List[Dict[str, Any]]:
        """
        Loads the conversation history from the JSON file.
        Returns an empty list if the file doesn't exist or is invalid.
        """
        if not HISTORY_PATH.exists():
            return []
        try:
            return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, TypeError):
            return []

    def _save_context(self):
        """Saves the current history list to the JSON file."""
        HISTORY_PATH.write_text(json.dumps(self.history, indent=4), encoding="utf-8")

    def add_message(self, role: str, content: str):
        """
        Adds a new message to the history and enforces the history limit.
        The history is immediately saved after the message is added.
        """
        if not isinstance(role, str) or not isinstance(content, str):
            return # Basic type safety

        self.history.append({"role": role, "content": content})

        # Enforce the history limit
        if len(self.history) > self.max_history_limit:
            self.history = self.history[-self.max_history_limit:]

        self._save_context()

    def get_recent_display(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        Returns the last N messages for display purposes.
        """
        return self.history[-n:]

    def update_limit(self, new_limit: int):
        """
        Updates the max_history_limit in the main config.json file.
        """
        if not isinstance(new_limit, int) or new_limit < 0:
            return

        self.max_history_limit = new_limit
        
        config_data = {}
        if CONFIG_PATH.exists():
            try:
                config_data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass # Start with a fresh dict if corrupt
        
        config_data["max_history_limit"] = self.max_history_limit
        CONFIG_PATH.write_text(json.dumps(config_data, indent=4), encoding="utf-8")
