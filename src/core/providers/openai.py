from openai import OpenAI
from typing import List, Dict, Any
from .base import BaseProvider

class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str, base_url: str = None):
        super().__init__(api_key, base_url)
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def list_models(self) -> List[str]:
        """
        Fetches a list of available model names from the OpenAI API.
        Returns an empty list if the API call fails.
        """
        try:
            return [model.id for model in self.client.models.list()]
        except Exception:
            return []

    def chat(self, model: str, messages: List[Dict[str, Any]], system_prompt: str) -> str:
        """
        Sends a chat completion request to the OpenAI API.
        """
        all_messages = [{"role": "system", "content": system_prompt}] + messages
        response = self.client.chat.completions.create(
            model=model,
            messages=all_messages,
        )
        return response.choices[0].message.content
