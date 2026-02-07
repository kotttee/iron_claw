from typing import Type, TYPE_CHECKING

from pydantic import BaseModel, Field

from src.interfaces.tool import BaseTool

if TYPE_CHECKING:
    from src.core.ai.schedule_manager import SchedulerManager

class ScheduleTaskArgs(BaseModel):
    task_description: str = Field(..., description="A clear and concise description of the recurring task to be executed.")
    cron_expression: str = Field(..., description="A standard 5-field cron expression for the recurring task (e.g., '0 9 * * MON-FRI').")

class ScheduleTaskTool(BaseTool):
    """
    Schedules a recurring task for the AI to perform at a later time.
    You must provide a standard cron_expression for the recurring schedule.
    The task_description should be a complete instruction for the AI,
    e.g., 'Write a morning summary of tech news every weekday at 9 AM'.
    For one-time tasks, use the 'standard/set_reminder' tool instead.
    """
    def __init__(self, scheduler: "SchedulerManager"):
        super().__init__()
        # Using __dict__ to avoid Pydantic model validation on the scheduler instance
        self.__dict__["scheduler"] = scheduler

    @property
    def name(self) -> str:
        return "standard/schedule_task"

    @property
    def description(self) -> str:
        return self.__doc__

    @property
    def args_schema(self) -> Type[BaseModel]:
        return ScheduleTaskArgs

    def execute(self, task_description: str, cron_expression: str) -> str:
        """Adds a recurring job to the SchedulerManager."""
        scheduler = self.__dict__["scheduler"]
        return scheduler.add_cron_job(cron_expression, task_description)

    def format_output(self, result: str) -> str:
        """Formats the raw scheduler result for a user-friendly output."""
        if result.startswith("Error"):
            return f"⚠️ {result}"
        job_id = result.split(":")[-1].strip()
        return f"🗓️ Recurring task scheduled successfully. ID: `{job_id}`"
