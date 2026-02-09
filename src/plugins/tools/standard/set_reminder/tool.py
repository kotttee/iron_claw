from datetime import datetime, timedelta
from typing import Optional, Any
from src.core.interfaces import BaseTool
from src.plugins.schedulers.schedule_manager.plugin import ScheduleManager
from .config import ReminderConfig

class SetReminderTool(BaseTool[ReminderConfig]):
    """
    Sets a one-time reminder. 
    Use 'delay_seconds' for relative time or 'timestamp' for absolute time.
    """
    name = "standard/set_reminder"
    config_class = ReminderConfig

    async def execute(self, 
                      message: str, 
                      delay_seconds: Optional[int] = None, 
                      timestamp: Optional[str] = None) -> str:
        
        if not delay_seconds and not timestamp:
            return "Error: Provide either 'delay_seconds' or 'timestamp'."

        run_at = None
        if delay_seconds:
            run_at = (datetime.now() + timedelta(seconds=delay_seconds)).isoformat()
        else:
            run_at = timestamp

        try:
            ScheduleManager.add_task("reminder", message, run_at)
            return f"Reminder set: '{message}' at {run_at}"
        except Exception as e:
            return f"Error: {e}"

    def format_output(self, result: Any) -> str:
        return f"🔔 {result}"

    async def healthcheck(self) -> tuple[bool, str]:
        return True, "Ready"
