from pydantic import BaseModel, Field

class ScheduleTaskArgs(BaseModel):
    task_description: str = Field(..., description="Description of the task to perform.")
    cron: str = Field(..., description="Cron expression for recurring execution.")
