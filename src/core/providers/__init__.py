from typing import Optional, Dict, Any

from .base import BaseProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .xai import XAIProvider

# A mapping from simple string names to the provider class.
PROVIDER_CLASS_MAP = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "xai": XAIProvider,
}

def get_provider(provider_config: Dict[str, Any], api_key: str) -> BaseProvider:
    """
    Factory function to get an instance of a provider from its configuration.
    """
    provider_type = provider_config.get("provider_type")
    if not provider_type or provider_type not in PROVIDER_CLASS_MAP:
        raise ValueError(f"Unknown provider type: '{provider_type}'. Check providers.json.")

    provider_class = PROVIDER_CLASS_MAP[provider_type]
    base_url = provider_config.get("base_url")
    
    return provider_class(api_key=api_key, base_url=base_url)
