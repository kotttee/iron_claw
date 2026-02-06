from typing import List, Dict, Any
import requests
import json

from .base import BaseProvider

class OpenAIProvider(BaseProvider):
    """
    A provider for OpenAI and any OpenAI-compatible APIs (like Groq, OpenRouter, etc.).
    """
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        super().__init__(api_key, base_url)
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def list_models(self) -> List[str]:
        """Fetches model names from the /models endpoint."""
        url = f"{self.base_url.rstrip('/')}/models"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Sort models, prioritizing 'gpt' and 'gemma' models first
            models = sorted(
                [model['id'] for model in data.get('data', []) if 'id' in model],
                key=lambda x: (not x.startswith(('gpt', 'gemma')), x)
            )
            return models
        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not fetch models from {url}. Error: {e}")
            return []

    def chat(self, model: str, messages: List[Dict[str, Any]], system_prompt: str) -> str:
        """Sends a chat completion request."""
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        
        # Prepend the system prompt to the message list
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        payload = {
            "model": model,
            "messages": full_messages,
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            content = data['choices'][0]['message']['content']
            return content.strip() if content else ""
        except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(f"Failed to get chat completion from {model}: {e}") from e
