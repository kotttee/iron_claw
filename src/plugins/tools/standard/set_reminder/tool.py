import pytz
from datetime import datetime, timedelta
from typing import Any
from typing import Optional
from src.core.interfaces import BaseTool
from .config import ReminderConfig



class SetReminderTool(BaseTool[ReminderConfig]):
    """
    Sets a one-time reminder for the user.
    """
    name = "standard/set_reminder"
    config_class = ReminderConfig

    async def execute(self, message: str, date: Optional[str] = None, timezone: str = "UTC",
                      in_minutes: Optional[int] = None, in_seconds: Optional[int] = None) -> str:
        """
        Sets a reminder.
        IMPORTANT: Always check the current time using a datetime tool or system knowledge before setting a specific date to ensure accuracy.

        Args:
            message: The reminder text.
            date: Specific date/time (YYYY-MM-DD HH:MM:SS).
            timezone: Timezone for the date (default UTC).
            in_minutes: Trigger in X minutes.
            in_seconds: Trigger in X seconds.
        """
        if not any([date, in_minutes, in_seconds]):
            return "Error: You must provide either 'date', 'in_minutes', or 'in_seconds'."

        run_at = None
        now = datetime.now()

        if in_seconds or in_minutes:
            seconds = (in_seconds or 0) + ((in_minutes or 0) * 60)
            run_at = (now + timedelta(seconds=seconds)).isoformat()

        elif date:
            try:
                dt = datetime.fromisoformat(date)

                user_tz = pytz.timezone(timezone)
                if dt.tzinfo is None:
                    dt = user_tz.localize(dt)
                else:
                    dt = dt.astimezone(user_tz)

                run_at = dt.astimezone().replace(tzinfo=None).isoformat()
            except Exception as e:
                return f"Error parsing date/timezone: {e}"

        try:
            # Используем системный планировщик через роутер
            task_id = await self.router.scheduler.add_task("reminder", message, run_at)
            return f"Reminder set: '{message}' at {run_at} (ID: {task_id})"
        except Exception as e:
            return f"Error setting reminder: {e}"


    def format_output(self, result: Any) -> str:
        return f"🔔 {result}"

    async def healthcheck(self) -> tuple[bool, str]:
        return True, "Ready"
