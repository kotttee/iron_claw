from typing import List, Dict, Any
from .base import BaseProvider
import xai_sdk
from xai_sdk.chat import user, system

class XAIProvider(BaseProvider):
    def __init__(self, api_key: str, base_url: str = None):
        super().__init__(api_key, base_url)
        self.client = xai_sdk.Client(api_key=self.api_key)

    def list_models(self) -> List[str]:
        """
        Fetches a list of available language models from the xAI API.
        Returns an empty list if the API call fails.
        """
        try:
            # The SDK returns a list of LanguageModel objects
            models = self.client.models.list_language_models()
            # Each object has a 'name' attribute (e.g., 'grok-1')
            return [model.name for model in models]
        except Exception:
            return []

    def chat(self, model: str, messages: List[Dict[str, Any]], system_prompt: str) -> str:
        """
        Sends a chat completion request to the xAI API.
        """
        conversation = [system(system_prompt)]
        for message in messages:
            if message["role"] == "user":
                conversation.append(user(message["content"]))
            # Note: The current xAI SDK chat flow might not explicitly handle 'assistant' messages
            # in the same way as OpenAI. We will only push user messages for now.

        response = self.client.chat.create(
            model=model,
            messages=conversation
        ).sample()

        return response.content
