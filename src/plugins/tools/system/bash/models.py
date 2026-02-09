from pydantic import BaseModel, Field

class ExecuteBashArgs(BaseModel):
    command: str = Field(..., description="The bash command to execute. Must be from the allowed list.")
