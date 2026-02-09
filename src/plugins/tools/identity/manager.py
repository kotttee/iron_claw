from pydantic import BaseModel, Field
from src.core.interfaces import BaseTool, ComponentConfig
from src.core.ai.memory import MemoryManager

class IdentityToolConfig(ComponentConfig):
    allow_self_modification: bool = True

class UpdateIdentityArgs(BaseModel):
    ai_persona: str = Field(..., description="The AI's persona and behavioral instructions in Markdown format.")
    user_goals: str = Field(..., description="The user's current goals and background information.")
    preferences: dict = Field(default_factory=dict, description="System preferences and settings.")

class UpdateIdentityTool(BaseTool[IdentityToolConfig]):
    """
    A tool that allows the AI to update its own identity, the user's profile, and system preferences.
    """
    name = "identity/update_identity"
    config_class = IdentityToolConfig

    async def execute(self, ai_persona: str, user_goals: str, preferences: dict) -> str:
        """
        Uses MemoryManager to save the updated identity and profile data.
        """
        try:
            updates = {
                "persona": ai_persona,
                "user_goals": user_goals,
                "preferences": preferences
            }
            MemoryManager.update_profile_static(updates)
            return "Identity and user profile updated successfully."
        except Exception as e:
            return f"Error updating identity: {e}"

    def format_output(self, result: str) -> str:
        """Formats the identity update result for user-facing output."""
        if "Error" in result:
            return f"⚠️ {result}"
        return "👤 AI identity and preferences have been successfully updated."

    async def healthcheck(self):
        return True, "OK"
