from pydantic import Field
from src.core.interfaces import ComponentConfig

class DateTimeConfig(ComponentConfig):
    enabled: bool = Field(True, description="Whether the date and time tool is active.")
    default_timezone: str = Field("UTC", description="The default timezone to use for date and time operations.")
