from src.core.interfaces import BaseTool
from src.core.ai.memory import MemoryManager
from .config import IdentityConfig
from typing import Any

class UpdatePersonaTool(BaseTool[IdentityConfig]):
    """
    Updates the AI's persona description (tone, style, behavior, and core instructions).
    """
    name = "identity/update_persona"
    config_class = IdentityConfig

    async def execute(self, content: str) -> str:
        try:
            MemoryManager.update_profile_static({"content": content})
            return f"AI content and persona updated: {content}"
        except Exception as e:
            return f"Error: {e}"

    def format_output(self, result: Any) -> str:
        return f"🎭 {result}"

    async def healthcheck(self): return True, "OK"

class UpdateUserGoalsTool(BaseTool[IdentityConfig]):
    """
    Updates the recorded goals and background information of the human user.
    """
    name = "identity/update_user_goals"
    config_class = IdentityConfig

    async def execute(self, goals: str) -> str:
        try:
            MemoryManager.update_profile_static({"user_goals": goals})
            return f"User goals updated to: {goals}"
        except Exception as e:
            return f"Error: {e}"

    def format_output(self, result: Any) -> str:
        return f"🎯 {result}"

    async def healthcheck(self): return True, "OK"

class UpdateAINameTool(BaseTool[IdentityConfig]):
    """
    Updates the AI's name and general identity information.
    """
    name = "identity/update_ai_name"
    config_class = IdentityConfig

    async def execute(self, name: str) -> str:
        try:
            MemoryManager.update_profile_static({"name": name})
            return f"AI Name updated to: {name}"
        except Exception as e:
            return f"Error: {e}"

    def format_output(self, result: Any) -> str:
        return f"👤 {result}"

    async def healthcheck(self): return True, "OK"
