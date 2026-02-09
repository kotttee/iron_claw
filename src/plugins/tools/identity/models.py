from pydantic import BaseModel, Field

class UpdatePersonaArgs(BaseModel):
    content: str = Field(..., description="The new core content, instructions, and persona description for the AI.")

class UpdateUserGoalsArgs(BaseModel):
    goals: str = Field(..., description="The new recorded goals of the user.")

class UpdateAINameArgs(BaseModel):
    name: str = Field(..., description="The new name for the AI.")
