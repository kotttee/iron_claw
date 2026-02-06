from typing import Optional

from .base import BaseProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
# Import other providers like xai.py here if you create them

# A mapping from simple string names to the provider class and its default base URL.
# This decouples the setup wizard from the provider implementations.
PROVIDER_REGISTRY = {
    "openai": (OpenAIProvider, "https://api.openai.com/v1"),
    "xai": (OpenAIProvider, "https://api.x.ai/v1"), # xAI uses an OpenAI-compatible API
    "groq": (OpenAIProvider, "https://api.groq.com/openai/v1"), # Groq also uses an OpenAI-compatible API
    "openrouter": (OpenAIProvider, "https://openrouter.ai/api/v1"),
    "anthropic": (AnthropicProvider, "https://api.anthropic.com/v1"),
    "ollama": (OpenAIProvider, "http://localhost:11434/v1"), # Local Ollama server
}

def get_provider(provider_name: str, api_key: str, base_url: Optional[str] = None) -> BaseProvider:
    """
    Factory function to get an instance of a provider.

    Args:
        provider_name: The name of the provider (e.g., 'openai', 'anthropic').
        api_key: The API key for the service.
        base_url: An optional custom base URL to override the default.

    Returns:
        An instance of a BaseProvider subclass.
        
    Raises:
        ValueError: If the provider name is not found in the registry.
    """
    provider_name = provider_name.lower()
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(f"Unknown provider: '{provider_name}'. Supported providers are: {list(PROVIDER_REGISTRY.keys())}")

    provider_class, default_base_url = PROVIDER_REGISTRY[provider_name]
    
    # Use the custom base_url if provided, otherwise use the default.
    final_base_url = base_url or default_base_url
    
    return provider_class(api_key=api_key, base_url=final_base_url)
