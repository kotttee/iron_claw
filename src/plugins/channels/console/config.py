from pydantic import Field
from src.core.interfaces import ComponentConfig

class ConsoleConfig(ComponentConfig):
    enabled: bool = Field(True, description="Whether the console channel is active.")
