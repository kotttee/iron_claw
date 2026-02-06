import json
from pathlib import Path
from typing import List, Dict, Any

from src.core.paths import MESSAGES_PATH, HISTORY_PATH, CONFIG_PATH

class ContextManager:
    """
    Manages the shared short-term (messages) and long-term (history) conversation context.
    It ensures that the contexts do not exceed their configured limits and
    persists them to their respective JSON files.
    """
    def __init__(self):
        """Initializes the ContextManager, loading configuration and contexts."""
        self.max_messages_limit = self._get_limit_from_config()
        self.max_history_limit = 100  # Fixed limit for long-term history

        self.messages = self._load_context(MESSAGES_PATH)
        self.history = self._load_context(HISTORY_PATH)

    def _get_limit_from_config(self) -> int:
        """Loads the messages limit from the main config file."""
        try:
            if CONFIG_PATH.exists():
                config_data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                # Using "max_history_limit" to maintain compatibility with existing configs
                return int(config_data.get("max_history_limit", 20))
        except (json.JSONDecodeError, ValueError):
            pass  # Fallback to default if file is corrupt or value is invalid
        return 20

    def _load_context(self, path: Path) -> List[Dict[str, Any]]:
        """
        Loads a conversation context from a JSON file.
        Returns an empty list if the file doesn't exist or is invalid.
        """
        if not path.exists():
            return []
        try:
            content = path.read_text(encoding="utf-8")
            if not content:
                return []
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return []

    def _save_messages(self):
        """Saves the current messages list to its JSON file."""
        MESSAGES_PATH.write_text(json.dumps(self.messages, indent=4), encoding="utf-8")

    def _save_history(self):
        """Saves the current history list to its JSON file."""
        HISTORY_PATH.write_text(json.dumps(self.history, indent=4), encoding="utf-8")

    def add_message(self, role: str, content: str):
        """
        Adds a new message to both messages and history, enforces their respective limits,
        and saves them.
        """
        if not isinstance(role, str) or not isinstance(content, str):
            return  # Basic type safety

        new_message = {"role": role, "content": content}

        # Add to messages (short-term) and enforce limit
        self.messages.append(new_message)
        if len(self.messages) > self.max_messages_limit:
            self.messages = self.messages[-self.max_messages_limit:]

        # Add to history (long-term) and enforce limit
        self.history.append(new_message)
        if len(self.history) > self.max_history_limit:
            self.history = self.history[-self.max_history_limit:]

        self._save_messages()
        self._save_history()

    def get_recent_display(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        Returns the last N messages from the short-term context for display purposes.
        """
        return self.messages[-n:]

    def update_limit(self, new_limit: int):
        """
        Updates the max_messages_limit in the main config.json file.
        """
        if not isinstance(new_limit, int) or new_limit < 0:
            return

        self.max_messages_limit = new_limit
        
        config_data = {}
        if CONFIG_PATH.exists():
            try:
                config_data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass  # Start with a fresh dict if corrupt
        
        # Using "max_history_limit" to maintain compatibility with existing configs
        config_data["max_history_limit"] = self.max_messages_limit
        CONFIG_PATH.write_text(json.dumps(config_data, indent=4), encoding="utf-8")
