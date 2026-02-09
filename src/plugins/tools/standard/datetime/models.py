from pydantic import BaseModel, Field

class GetCurrentDateTimeArgs(BaseModel):
    timezone: str = Field("UTC", description="The timezone to use, e.g., 'UTC', 'America/New_York'.")
