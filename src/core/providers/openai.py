from openai import OpenAI

from .base import BaseProvider
from typing import List, Dict


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str, base_url: str = None):
        super().__init__(api_key, base_url)

        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def list_models(self) -> List[str]:
        try:
            return [m.id for m in self.client.models.list()]
        except Exception:
            return ["gpt-4o", "gpt-4-turbo"]

    def chat(self, model: str, messages: List[Dict[str, str]], system_prompt: str) -> str:
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        response = self.client.chat.completions.create(
            model=model,
            messages=full_messages
        )
        return response.choices[0].message.content
