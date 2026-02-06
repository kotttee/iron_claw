import datetime
from typing import Optional, Type, TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

from src.interfaces.tool import BaseTool

if TYPE_CHECKING:
    from src.core.ai.router import Router
    from src.core.ai.schedule_manager import SchedulerManager

class ScheduleTaskArgs(BaseModel):
    task_description: str = Field(..., description="A clear and concise description of the task to be executed.")
    iso_timestamp: Optional[str] = Field(None, description="A specific time in ISO 8601 format for a one-time task (e.g., '2023-10-27T10:00:00').")
    cron_expression: Optional[str] = Field(None, description="A standard 5-field cron expression for a recurring task (e.g., '0 9 * * MON-FRI').")

    @model_validator(mode='before')
    def check_timestamp_or_cron(cls, values):
        """Ensures that exactly one of the timing arguments is provided."""
        if bool(values.get('iso_timestamp')) == bool(values.get('cron_expression')):
            raise ValueError('Exactly one of "iso_timestamp" or "cron_expression" must be provided.')
        return values

class ScheduleTaskTool(BaseTool):
    """
    Schedules a task for the AI to perform at a later time.
    You must provide either a specific time (iso_timestamp) for a one-time task
    or a recurring schedule (cron_expression).
    The task_description should be a complete instruction for the AI,
    e.g., 'Write a morning summary of tech news'.
    """
    def __init__(self, router: "Router"):
        super().__init__()
        # The scheduler is now managed by the ScheduleManager, which is initialized alongside the Router.
        # We need a way to access it. Let's assume the main application passes it to the router or a central place.
        # For now, we'll assume the router has a reference to the scheduler manager.
        # This might require a change in how the application is wired up.
        if not hasattr(router, 'scheduler_manager'):
            raise AttributeError("The Router is not initialized with a SchedulerManager instance.")
        self.scheduler: "SchedulerManager" = router.scheduler_manager

    @property
    def name(self) -> str:
        return "schedule_task"

    @property
    def description(self) -> str:
        return self.__doc__

    @property
    def args_schema(self) -> Type[BaseModel]:
        return ScheduleTaskArgs

    def execute(self, task_description: str, iso_timestamp: Optional[str] = None, cron_expression: Optional[str] = None) -> str:
        """Adds a job to the SchedulerManager."""
        if iso_timestamp:
            try:
                run_date = datetime.datetime.fromisoformat(iso_timestamp)
                return self.scheduler.add_date_job(run_date, task_description)
            except ValueError:
                return "Error: Invalid ISO 8601 timestamp format. Please use YYYY-MM-DDTHH:MM:SS."
        elif cron_expression:
            return self.scheduler.add_cron_job(cron_expression, task_description)

        return "Error: You must provide either a valid iso_timestamp or a cron_expression."
