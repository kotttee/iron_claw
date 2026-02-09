from pydantic import Field
from src.core.interfaces import ComponentConfig

class IdentityConfig(ComponentConfig):
    enabled: bool = Field(True, description="Whether the identity management tool is active.")
