import datetime
from typing import Optional, Type, TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from src.core.scheduler import SchedulerManager

from src.interfaces.tool import BaseTool

class ScheduleTaskArgs(BaseModel):
    message: str = Field(..., description="The task or reminder message for the user.")
    iso_timestamp: Optional[str] = Field(None, description="A specific time in ISO 8601 format for a one-time task.")
    cron_expression: Optional[str] = Field(None, description="A standard 5-field cron expression for a recurring task (e.g., '0 9 * * MON').")
    plugin_id: str = Field(..., description="The ID of the channel where the user made the request.")
    user_id: str = Field(..., description="The user's unique identifier within that channel.")

    @model_validator(mode='before')
    def check_timestamp_or_cron(cls, values):
        """Ensure that either iso_timestamp or cron_expression is provided, but not both."""
        if bool(values.get('iso_timestamp')) == bool(values.get('cron_expression')):
            raise ValueError('Exactly one of "iso_timestamp" or "cron_expression" must be provided.')
        return values

class ScheduleTaskTool(BaseTool):
    """A tool to schedule tasks, either as a one-time reminder or a recurring cron job."""

    def __init__(self, scheduler: "SchedulerManager"):
        super().__init__()
        self.scheduler = scheduler

    @property
    def name(self) -> str:
        return "standard/schedule_task"

    @property
    def description(self) -> str:
        return "Schedules a task. Use 'iso_timestamp' for a one-time event or 'cron_expression' for a recurring event."

    @property
    def args_schema(self) -> Type[BaseModel]:
        return ScheduleTaskArgs

    def execute(self, message: str, plugin_id: str, user_id: str, iso_timestamp: Optional[str] = None, cron_expression: Optional[str] = None) -> str:
        """
        Parses arguments and adds a job to the SchedulerManager.
        """
        context = {"plugin_id": plugin_id, "user_id": user_id}

        if iso_timestamp:
            try:
                run_date = datetime.datetime.fromisoformat(iso_timestamp)
                if run_date <= datetime.datetime.now(run_date.tzinfo):
                    return "Error: Scheduled time must be in the future."
                return self.scheduler.add_date_job(run_date, message, context)
            except ValueError:
                return "Error: Invalid ISO 8601 timestamp format. Use 'YYYY-MM-DDTHH:MM:SS'."

        elif cron_expression:
            return self.scheduler.add_cron_job(cron_expression, message, context)

        return "Error: Could not schedule task. A valid timestamp or cron expression is required."
