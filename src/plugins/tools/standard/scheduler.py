import datetime
from typing import Optional, Type, TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

from src.interfaces.tool import BaseTool

if TYPE_CHECKING:
    from src.core.router import MessageRouter
    from src.core.scheduler import SchedulerManager

class ScheduleTaskArgs(BaseModel):
    message: str = Field(..., description="The task or reminder message for the user.")
    iso_timestamp: Optional[str] = Field(None, description="A specific time in ISO 8601 format for a one-time task.")
    cron_expression: Optional[str] = Field(None, description="A standard 5-field cron expression for a recurring task.")
    target_channel: str = Field("auto", description="The channel to send the notification to (e.g., 'channel/telegram_bot', 'console'). If 'auto', sends to the last active channel.")

    @model_validator(mode='before')
    def check_timestamp_or_cron(cls, values):
        if bool(values.get('iso_timestamp')) == bool(values.get('cron_expression')):
            raise ValueError('Exactly one of "iso_timestamp" or "cron_expression" must be provided.')
        return values

class ScheduleTaskTool(BaseTool):
    """
    Schedules a task. Use 'iso_timestamp' for a one-time event or 'cron_expression' for a recurring event.
    If the user says 'remind me in telegram', set target_channel='channel/telegram_bot'. If unspecified, use 'auto'.
    """
    def __init__(self, router: "MessageRouter"):
        super().__init__()
        self.router = router
        self.scheduler = router.scheduler # Get scheduler from router

    @property
    def name(self) -> str:
        return "standard/schedule_task"
    @property
    def description(self) -> str:
        return self.__doc__
    @property
    def args_schema(self) -> Type[BaseModel]:
        return ScheduleTaskArgs

    def execute(self, message: str, target_channel: str, iso_timestamp: Optional[str] = None, cron_expression: Optional[str] = None) -> str:
        """Parses arguments and adds a job to the SchedulerManager with routing info."""
        
        contact_info = None
        if target_channel == "auto":
            contact_info = self.router.get_preferred_output_channel()
            if not contact_info:
                return "Error: Cannot determine target channel automatically. No recent user interaction found."
        else:
            # In a multi-user system, you'd look up the user's specific contact ID for that channel.
            # For now, we assume the last known ID for that channel is correct.
            preferred = self.router.get_preferred_output_channel()
            if preferred and preferred.get("plugin_id") == target_channel:
                 contact_info = preferred
            else:
                return f"Error: No contact information found for the specified channel '{target_channel}'."

        if not contact_info:
            return "Error: Could not resolve a target for the notification."

        context = {
            "plugin_id": contact_info["plugin_id"],
            "user_contact_id": contact_info["user_contact_id"]
        }

        if iso_timestamp:
            try:
                run_date = datetime.datetime.fromisoformat(iso_timestamp)
                return self.scheduler.add_date_job(run_date, message, context)
            except ValueError:
                return "Error: Invalid ISO 8601 timestamp format."
        elif cron_expression:
            return self.scheduler.add_cron_job(cron_expression, message, context)

        return "Error: A valid timestamp or cron expression is required."
