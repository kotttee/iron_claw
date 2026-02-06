import json
from abc import ABC, abstractmethod
from dotenv import set_key, get_key

# Refactored to use the centralized pathing system
from .paths import PLUGINS_DIR, ENV_PATH

class ConfigurablePlugin(ABC):
    """
    An abstract base class for stateful, configurable plugins (Channels and Tools).
    Handles loading/saving of configuration and state (enabled/disabled).
    """
    def __init__(self, name: str, category: str):
        """
        Initializes the plugin, setting up its configuration path.

        Args:
            name (str): The unique name of the plugin (e.g., 'telegram', 'weather').
            category (str): The category of the plugin ('channel' or 'tool').
        """
        if not name or not category:
            raise ValueError("Plugin name and category cannot be empty.")
            
        self.name = name
        self.category = category
        # create path
        self.directory = PLUGINS_DIR / self.name
        self.directory.mkdir(parents=True, exist_ok=True)
        self.config_path = self.directory / f"config.json"
        self.config: dict = {}
        self.load_config()

    def load_config(self):
        """
        Loads the plugin's configuration from its JSON file.
        If the file doesn't exist, initializes with an empty dictionary.
        """
        ensure_dirs()  # Ensure ~/.iron_claw/data/configs exists
        if self.config_path.exists():
            try:
                self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, TypeError):
                self.config = {} # Start fresh if config is corrupted
        else:
            # For the console, default to enabled.
            if self.name == "console":
                 self.config = {"enabled": True}
            else:
                 self.config = {"enabled": False}

    def save_config(self):
        """
        Saves the current configuration dictionary to its JSON file.
        """
        self.config_path.write_text(json.dumps(self.config, indent=4), encoding="utf-8")

    def is_enabled(self) -> bool:
        """
        Checks if the plugin is marked as enabled in its configuration.
        Defaults to False if not set, except for the 'console' channel.
        """
        return self.config.get('enabled', False)

    def toggle_enabled(self) -> bool:
        """
        Toggles the 'enabled' state of the plugin, saves the configuration,
        and returns the new state.
        """
        new_state = not self.is_enabled()
        self.config['enabled'] = new_state
        self.save_config()
        return new_state

    def _save_secret(self, key: str, value: str):
        """
        Saves a secret key-value pair to the project's .env file.

        Args:
            key (str): The environment variable name (e.g., 'TELEGRAM_TOKEN').
            value (str): The secret value to save.
        """
        ensure_dirs()
        if not ENV_PATH.exists():
            ENV_PATH.touch()
        
        set_key(str(ENV_PATH), key, value)

    def _get_secret(self, key: str) -> str | None:
        """
        Retrieves a secret value from the project's .env file.
        """
        return get_key(str(ENV_PATH), key)

    @abstractmethod
    def setup_wizard(self):
        """
        An abstract method that should implement an interactive setup process
        for the plugin using a TUI library like `questionary`. This method
        is responsible for updating `self.config` and calling `self.save_config()`.
        """
        raise NotImplementedError("Each plugin must implement its own setup wizard.")

    def get_status_emoji(self) -> str:
        """Returns a status emoji based on whether the plugin is enabled."""
        return "🟢" if self.is_enabled() else "🔴"
