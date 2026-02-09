from typing import Any
from src.core.interfaces import BaseTool
from .config import SchedulerToolConfig

class ScheduleTaskTool(BaseTool[SchedulerToolConfig]):
    """
    Schedules a recurring task for the AI using a cron expression.
    """
    name = "standard/schedule_task"
    config_class = SchedulerToolConfig

    async def execute(self, task_description: str, cron: str) -> str:
        """Schedules a recurring task via the central ScheduleManager."""
        try:
            # Используем системный планировщик через router
            if not hasattr(self, 'router') or not self.router.scheduler:
                return "Error: Scheduler system is not initialized in Router."
            
            await self.router.scheduler.add_task("cron", task_description, cron)
            return f"Recurring task scheduled: {task_description} (Cron: {cron})"
        except Exception as e:
            return f"Error: {e}"

    def format_output(self, result: Any) -> str:
        return f"🗓️ {result}"

    async def healthcheck(self) -> tuple[bool, str]:
        return True, "Scheduler tool ready."
