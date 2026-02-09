from pydantic import BaseModel, Field
from typing import Optional, Dict

class UpdateAIIdentityArgs(BaseModel):
    name: Optional[str] = Field(None, description="New name for the AI.")
    content: Optional[str] = Field(None, description="New core instructions/persona.")

class UpdateUserPersonaArgs(BaseModel):
    user_name: Optional[str] = Field(None, description="The user's name.")
    user_goals: Optional[str] = Field(None, description="The user's goals.")

class UpdatePreferencesArgs(BaseModel):
    timezone: Optional[str] = Field(None, description="User's timezone.")
    preferences: Optional[Dict[str, str]] = Field(None, description="Other text preferences.")
