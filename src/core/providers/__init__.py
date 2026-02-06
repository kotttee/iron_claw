import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Type

# Refactored to use the centralized pathing system
from ..paths import PROVIDERS_JSON_PATH
from .base import BaseProvider
from .openai import OpenAIProvider
from .xai import XAIProvider
# from .anthropic import AnthropicProvider # This would be needed for Anthropic support

# Maps the 'provider_type' string from JSON to the actual Python class.
PROVIDER_CLASS_MAP: Dict[str, Type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "xai": XAIProvider,
    # "anthropic": AnthropicProvider,
}

class ProviderFactory:
    """
    Handles loading and creating LLM providers based on a central JSON configuration.
    This class is a singleton to ensure the config is loaded only once.
    """
    _instance = None
    _providers_config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProviderFactory, cls).__new__(cls)
            # Refactored to use the centralized path from paths.py
            cls._instance._load_config(PROVIDERS_JSON_PATH)
        return cls._instance

    def _load_config(self, config_path: Path):
        """Loads the provider definitions from the specified JSON file."""
        if not config_path.exists():
            self._providers_config = {}
            return
        try:
            self._providers_config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self._providers_config = {}

    def get_provider_names(self) -> List[str]:
        """Returns a list of user-friendly provider names from providers.json."""
        return list(self._providers_config.keys())

    def get_provider_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Gets the raw configuration for a provider by its display name."""
        return self._providers_config.get(name)

    def create_provider(self, name: str, api_key: str) -> BaseProvider:
        """
        Creates an instance of a provider using its display name.

        Args:
            name: The display name from providers.json (e.g., "OpenAI", "xAI (Grok)").
            api_key: The API key for the provider.

        Returns:
            An instance of the corresponding BaseProvider subclass.

        Raises:
            ValueError: If the provider name is not found, its class is not mapped,
                        or the API key is empty.
        """
        config = self.get_provider_config(name)
        if not config:
            raise ValueError(f"Provider '{name}' not found in providers.json.")

        provider_type = config.get("provider_type")
        base_url = config.get("base_url")

        provider_class = PROVIDER_CLASS_MAP.get(provider_type)
        if not provider_class:
            raise ValueError(f"Provider type '{provider_type}' for '{name}' is not mapped to a Python class in PROVIDER_CLASS_MAP.")

        if not api_key:
            raise ValueError("API key cannot be empty.")

        return provider_class(api_key=api_key, base_url=base_url)

# A singleton instance for easy access throughout the application.
provider_factory = ProviderFactory()
