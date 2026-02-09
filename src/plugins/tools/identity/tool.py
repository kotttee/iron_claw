from src.core.interfaces import BaseTool
from src.core.ai.memory import MemoryManager
from .config import IdentityConfig

class UpdatePersonaTool(BaseTool[IdentityConfig]):
    """
    Updates the AI's persona description (tone, style, behavior).
    """
    name = "identity/update_persona"
    config_class = IdentityConfig

    async def execute(self, persona: str) -> str:
        try:
            MemoryManager.update_profile_static({"persona": persona})
            return f"Persona updated to: {persona}"
        except Exception as e:
            return f"Error: {e}"

    async def healthcheck(self): return True, "OK"

class UpdateUserGoalsTool(BaseTool[IdentityConfig]):
    """
    Updates the recorded goals of the user.
    """
    name = "identity/update_user_goals"
    config_class = IdentityConfig

    async def execute(self, goals: str) -> str:
        try:
            MemoryManager.update_profile_static({"user_goals": goals})
            return f"User goals updated to: {goals}"
        except Exception as e:
            return f"Error: {e}"

    async def healthcheck(self): return True, "OK"
