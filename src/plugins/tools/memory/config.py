from pydantic import Field
from src.core.interfaces import ComponentConfig

class MemoryToolConfig(ComponentConfig):
    enabled: bool = Field(True, description="Whether the memory tool is active.")
