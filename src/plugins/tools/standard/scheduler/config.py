from pydantic import Field
from src.core.interfaces import ComponentConfig

class SchedulerToolConfig(ComponentConfig):
    enabled: bool = Field(True, description="Whether the scheduler tool is active.")
