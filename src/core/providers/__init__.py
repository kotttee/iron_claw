from typing import Optional
from .base import BaseProvider
from .openai import OpenAIProvider
from .xai import XAIProvider
# Assuming a LocalProvider might exist in local.py, but will handle its absence.
# from .local import LocalProvider

PROVIDER_CLASS_MAP = {
    "openai": OpenAIProvider,
    "xai": XAIProvider,
    "grok": XAIProvider, # Alias for xai
    # "local": LocalProvider,
}

def get_provider(name: str, api_key: str, base_url: Optional[str] = None) -> BaseProvider:
    """
    Factory function to get an instance of a provider.

    Args:
        name: The name of the provider (e.g., "openai", "xai", "grok").
        api_key: The API key for the provider.
        base_url: The optional base URL for the provider's API.

    Returns:
        An instance of the specified provider.

    Raises:
        ValueError: If the provider name is unknown.
    """
    provider_name = name.lower()
    provider_class = PROVIDER_CLASS_MAP.get(provider_name)

    if not provider_class:
        raise ValueError(f"Unknown provider: '{name}'. Supported providers are: {list(PROVIDER_CLASS_MAP.keys())}")

    return provider_class(api_key=api_key, base_url=base_url)
