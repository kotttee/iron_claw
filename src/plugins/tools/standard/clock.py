import datetime
from typing import Type, TYPE_CHECKING

from pydantic import BaseModel, Field

from src.interfaces.tool import BaseTool

if TYPE_CHECKING:
    pass

class SetReminderArgs(BaseModel):
    iso_timestamp: str = Field(..., description="The reminder time in strict ISO 8601 format (e.g., '2024-08-15T10:30:00').")
    message: str = Field(..., description="The reminder message for the user.")
    plugin_id: str = Field(..., description="The ID of the channel plugin where the user made the request (e.g., 'telegram', 'console').")
    user_id: str = Field(..., description="The unique identifier for the user within that channel.")

class SetReminderTool(BaseTool):
    """A tool to set a reminder for the user."""

    def __init__(self, scheduler: "SchedulerManager"):
        super().__init__()
        self.scheduler = scheduler

    @property
    def name(self) -> str:
        return "standard/set_reminder"

    @property
    def description(self) -> str:
        return "Sets a reminder for the user. The LLM must convert natural language time into a precise ISO 8601 timestamp."

    @property
    def args_schema(self) -> Type[BaseModel]:
        return SetReminderArgs

    def execute(self, iso_timestamp: str, message: str, plugin_id: str, user_id: str) -> str:
        """
        Parses the arguments and adds a reminder job to the SchedulerManager.
        """
        try:
            run_date = datetime.datetime.fromisoformat(iso_timestamp)
            
            # Ensure the time is in the future
            if run_date <= datetime.datetime.now():
                return "Error: Reminder time must be in the future."

            context = {"plugin_id": plugin_id, "user_id": user_id}
            return self.scheduler.add_reminder(run_date, message, context)
            
        except ValueError:
            return "Error: Invalid ISO 8601 timestamp format. Please use the format 'YYYY-MM-DDTHH:MM:SS'."
        except Exception as e:
            return f"An unexpected error occurred: {e}"
