from abc import ABC, abstractmethod
from typing import Type, Any, Dict

from pydantic import BaseModel, Field

class BaseTool(ABC, BaseModel):
    """
    Abstract Base Class for all tool plugins.

    Tools are functions that the AI agent can execute, such as reading a file,
    searching the web, or interacting with an API.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """A unique identifier for the tool (e.g., 'file_reader', 'web_search')."""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """A description of what the tool does, used by the LLM to decide when to use it."""
        raise NotImplementedError

    @property
    @abstractmethod
    def args_schema(self) -> Type[BaseModel]:
        """The Pydantic model for the tool's arguments."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Executes the tool with the given arguments."""
        raise NotImplementedError

    def to_openai_schema(self) -> Dict[str, Any]:
        """
        Converts the tool's Pydantic model into a JSON schema compatible with OpenAI's API.
        """
        schema = self.args_schema.model_json_schema()
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", []),
                },
            },
        }
