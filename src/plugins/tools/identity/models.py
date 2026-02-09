from pydantic import BaseModel, Field

class UpdatePersonaArgs(BaseModel):
    persona: str = Field(..., description="The new persona description (tone, style, behavior).")

class UpdateUserGoalsArgs(BaseModel):
    goals: str = Field(..., description="The new recorded goals of the user.")
