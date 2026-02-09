from pydantic import Field
from src.core.interfaces import IntervalConfig

class ScheduleManagerConfig(IntervalConfig):
    enabled: bool = Field(True, description="Whether the schedule manager is active.")
    interval_seconds: int = Field(30, description="How often (in seconds) to check for scheduled tasks.")
