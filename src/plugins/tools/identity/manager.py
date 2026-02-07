from typing import Type
from pydantic import BaseModel, Field
from src.interfaces.tool import BaseTool
from src.core.ai.identity_manager import IdentityManager

class UpdateIdentityArgs(BaseModel):
    ai_persona: str = Field(..., description="The AI's persona and behavioral instructions in Markdown format.")
    user_profile: str = Field(..., description="The user's profile and background information in Markdown format.")
    preferences: str = Field(..., description="The system preferences and settings in Markdown format.")

class UpdateIdentityTool(BaseTool):
    """
    A tool that allows the AI to update its own identity, the user's profile, and system preferences.
    """
    @property
    def name(self) -> str:
        return "identity/update_identity"

    @property
    def description(self) -> str:
        return "Updates the AI persona, user profile, and system preferences markdown files. Use this to persist changes to who you are, what you know about the user, or system-wide settings."

    @property
    def args_schema(self) -> Type[BaseModel]:
        return UpdateIdentityArgs

    def execute(self, ai_persona: str, user_profile: str, preferences: str) -> str:
        """
        Uses IdentityManager to save the updated identity files.
        """
        manager = IdentityManager()
        return manager.run(ai_persona, user_profile, preferences)

    def format_output(self, result: str) -> str:
        """Formats the identity update result for user-facing output."""
        if "Error" in result:
            return f"⚠️ {result}"
        return "👤 AI identity and preferences have been successfully updated."
