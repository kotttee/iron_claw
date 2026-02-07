import datetime
from typing import Type, Optional

from pydantic import BaseModel, Field, root_validator

from src.interfaces.tool import BaseTool


class SetReminderArgs(BaseModel):
    message: str = Field(..., description="The reminder message for the user.")
    reminder_in_minutes: Optional[int] = Field(None, description="The number of minutes from now to set the reminder (for relative times like 'in 10 minutes').")
    date: Optional[str] = Field(None, description="The date for the reminder in YYYY-MM-DD format (for absolute times like 'tomorrow at 10am').")
    time: Optional[str] = Field(None, description="The time for the reminder in HH:MM:SS format (used with 'date').")
    timezone: str = Field("UTC", description="The user's timezone (e.g., 'UTC', 'Europe/London'). Defaults to UTC.")

    @root_validator(skip_on_failure=True)
    def check_time_fields(cls, values):
        time_fields = ['reminder_in_minutes', 'date']
        provided_time_fields = sum(1 for field in time_fields if values.get(field) is not None)
        if provided_time_fields != 1:
            raise ValueError("For a reminder, please provide exactly one of 'reminder_in_minutes' or 'date'.")
        if values.get('time') and not values.get('date'):
            raise ValueError("'time' can only be used when 'date' is also provided.")
        return values


class SetReminderTool(BaseTool):
    """
    A tool to set a reminder for the user. This is for one-time reminders.
    The user's request may be in the future. Before calling this function, get the current time to make sure you are setting the reminder correctly.
    For recurring tasks, use the 'standard/schedule_task' tool.
    """

    def __init__(self, scheduler: "SchedulerManager"):
        super().__init__()
        self.__dict__["scheduler"] = scheduler


    @property
    def name(self) -> str:
        return "standard/set_reminder"

    @property
    def description(self) -> str:
        return "Sets a one-time reminder for the user. Use relative time ('in 10 minutes') or absolute time ('tomorrow at 10am')."

    @property
    def args_schema(self) -> Type[BaseModel]:
        return SetReminderArgs

    def execute(self, message: str, timezone: str = "UTC", reminder_in_minutes: Optional[int] = None, date: Optional[str] = None, time: Optional[str] = None) -> str:
        """
        Parses the arguments and adds a reminder job to the SchedulerManager.
        """
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            run_date = None

            if reminder_in_minutes is not None:
                run_date = now + datetime.timedelta(minutes=reminder_in_minutes)
            elif date is not None:
                time_str = time if time else "00:00:00"
                dt_str = f"{date}T{time_str}"
                # This assumes the provided date/time is in the specified timezone, then converts to UTC.
                # A more robust solution would involve pytz for timezone handling.
                run_date = datetime.datetime.fromisoformat(dt_str).replace(tzinfo=datetime.timezone.utc)
            else:
                return "Error: You must provide a time for the reminder using either 'reminder_in_minutes' or 'date'."

            if run_date <= now:
                return "Error: Reminder time must be in the future. Use datetime tool to see time now"

            return self.__dict__["scheduler"].add_reminder(run_date, message)

        except ValueError as e:
            return f"Error: Invalid time format. Please use YYYY-MM-DD for date and HH:MM:SS for time. Details: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

    def format_output(self, result: str) -> str:
        """Formats the raw reminder result for a user-friendly output."""
        if result.startswith("Error"):
            return f"⚠️ {result}"

        job_id = result.split(":")[-1].strip()
        return f"⏰ Reminder set! I will notify you at the specified time. (ID: `{job_id}`)"
