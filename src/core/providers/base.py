from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseProvider(ABC):
    """
    Abstract Base Class for all LLM providers.
    This defines the standard interface for listing models and generating chat completions.
    """
    def __init__(self, api_key: str, base_url: str = None):
        """
        Initializes the provider with an API key and an optional base URL.

        Args:
            api_key: The API key for the provider.
            base_url: The base URL for the API endpoint.
        """
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    def list_models(self) -> List[str]:
        """
        Fetches a list of available model names from the provider's API.
        If an error occurs, it should return an empty list.

        Returns:
            A list of strings, where each string is a model identifier.
        """
        raise NotImplementedError

    @abstractmethod
    def chat(self, model: str, messages: List[Dict[str, Any]], system_prompt: str) -> str:
        """
        Sends a chat completion request to the provider's API.

        Args:
            model: The specific model to use for the completion.
            messages: A list of message dictionaries (e.g., {'role': 'user', 'content': '...'})
            system_prompt: The system prompt to guide the model's behavior.

        Returns:
            The text content of the assistant's response.
        """
        raise NotImplementedError
