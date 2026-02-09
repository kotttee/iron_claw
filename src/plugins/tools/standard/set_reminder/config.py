from pydantic import Field
from src.core.interfaces import ComponentConfig

class ReminderConfig(ComponentConfig):
    enabled: bool = Field(True, description="Whether the reminder tool is active.")
