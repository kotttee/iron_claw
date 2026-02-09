from src.core.interfaces import BaseTool
from src.core.ai.memory import MemoryManager
from .config import IdentityConfig
from typing import Any

class UpdateAIIdentityTool(BaseTool[IdentityConfig]):
    """
    Updates the AI's own identity (name and core persona/content).
    """
    name = "identity/update_ai_identity"
    config_class = IdentityConfig

    async def execute(self, name: str = None, content: str = None) -> str:
        try:
            updates = {}
            if name: updates["name"] = name
            if content: updates["content"] = content
            MemoryManager.update_profile_static(updates)
            return f"AI Identity updated: {updates}"
        except Exception as e:
            return f"Error: {e}"

    def format_output(self, result: Any) -> str:
        return f"🎭 {result}"

    async def healthcheck(self) -> tuple[bool, str]: return True, "OK"

class UpdateUserPersonaTool(BaseTool[IdentityConfig]):
    """
    Updates the user's persona (their name and goals).
    """
    name = "identity/update_user_persona"
    config_class = IdentityConfig

    async def execute(self, user_name: str = None, user_goals: str = None) -> str:
        try:
            updates = {}
            if user_name: updates["user_name"] = user_name
            if user_goals: updates["user_goals"] = user_goals
            MemoryManager.update_profile_static(updates)
            return f"User Persona updated: {updates}"
        except Exception as e:
            return f"Error: {e}"

    def format_output(self, result: Any) -> str:
        return f"🎯 {result}"

    async def healthcheck(self) -> tuple[bool, str]: return True, "OK"

class UpdatePreferencesTool(BaseTool[IdentityConfig]):
    """
    Updates system preferences like timezone and other text-based settings.
    """
    name = "identity/update_preferences"
    config_class = IdentityConfig

    async def execute(self, timezone: str = None, preferences: dict = None) -> str:
        try:
            updates = {}
            if timezone: updates["timezone"] = timezone
            if preferences: updates["preferences"] = preferences
            MemoryManager.update_profile_static(updates)
            return f"Preferences updated: {updates}"
        except Exception as e:
            return f"Error: {e}"

    def format_output(self, result: Any) -> str:
        return f"⚙️ {result}"

    async def healthcheck(self) -> tuple[bool, str]: return True, "OK"
