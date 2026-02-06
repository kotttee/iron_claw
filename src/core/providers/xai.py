from .base import BaseProvider
from typing import List, Dict

from xai_sdk import Client
from xai_sdk.chat import user, system, assistant


class XAIProvider(BaseProvider):
    def __init__(self, api_key: str, base_url: str = None):
        super().__init__(api_key, base_url)

        if Client is None:
            raise ImportError("xai-sdk not found. Run: pip install xai-sdk")

        self.client = Client(api_key=api_key)

    def list_models(self) -> List[str]:
        return ["grok-2-latest", "grok-2", "grok-beta"]

    def chat(self, model: str, messages: List[Dict[str, str]], system_prompt: str) -> str:
        chat_session = self.client.chat.create(model=model)
        chat_session.append(system(system_prompt))

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role == "user":
                chat_session.append(user(content))
            elif role == "assistant":
                chat_session.append(assistant(content))

        response = chat_session.sample()
        return response.content