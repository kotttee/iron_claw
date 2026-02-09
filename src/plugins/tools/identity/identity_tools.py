from pydantic import BaseModel, Field
from src.core.interfaces import BaseTool
from src.core.ai.memory import MemoryManager

class UpdatePersonaTool(BaseTool[BaseModel]):
    """
    Updates the AI's persona description (tone, style, behavior).
    """
    name = "identity/update_persona"
    config_class = BaseModel

    async def execute(self, persona: str) -> str:
        try:
            MemoryManager.update_profile_static({"persona": persona})
            return f"Persona updated to: {persona}"
        except Exception as e:
            return f"Error: {e}"

    async def healthcheck(self): return True, "OK"

class UpdateUserGoalsTool(BaseTool[BaseModel]):
    """
    Updates the recorded goals of the user.
    """
    name = "identity/update_user_goals"
    config_class = BaseModel

    async def execute(self, goals: str) -> str:
        try:
            MemoryManager.update_profile_static({"user_goals": goals})
            return f"User goals updated to: {goals}"
        except Exception as e:
            return f"Error: {e}"

    async def healthcheck(self): return True, "OK"