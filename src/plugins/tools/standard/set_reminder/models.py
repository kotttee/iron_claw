from pydantic import BaseModel, Field
from typing import Optional

class SetReminderArgs(BaseModel):
    message: str = Field(..., description="The reminder message.")
    delay_seconds: Optional[int] = Field(None, description="Delay in seconds from now.")
    timestamp: Optional[str] = Field(None, description="Absolute timestamp (YYYY-MM-DD HH:MM:SS).")
