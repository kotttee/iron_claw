from typing import List, Dict, Any
import requests
import json

from .base import BaseProvider

class AnthropicProvider(BaseProvider):
    """
    A provider for Anthropic's unique API (Claude models).
    """
    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com/v1"):
        super().__init__(api_key, base_url)
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

    def list_models(self) -> List[str]:
        """
        Anthropic does not have a public /models endpoint.
        Returns a hardcoded list of known, popular models.
        """
        return [
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]

    def chat(self, model: str, messages: List[Dict[str, Any]], system_prompt: str) -> str:
        """
        Sends a chat completion request using Anthropic's /messages endpoint.
        """
        url = f"{self.base_url.rstrip('/')}/messages"
        
        # Anthropic requires the 'system' prompt at the top level.
        # It also requires that user/assistant messages alternate.
        # This implementation assumes a valid alternating sequence.
        payload = {
            "model": model,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": 4096, # Anthropic requires max_tokens
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            # The response content is in a list of blocks.
            text_blocks = [block['text'] for block in data.get('content', []) if block['type'] == 'text']
            return "".join(text_blocks).strip()
        except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(f"Failed to get chat completion from {model}: {e}") from e
