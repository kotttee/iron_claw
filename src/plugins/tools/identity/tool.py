from src.core.interfaces import BaseTool
from src.core.ai.memory import MemoryManager
from .config import IdentityConfig
from typing import Any

class UpdateIdentityTool(BaseTool[IdentityConfig]):
    """
    Updates the entire AI identity, user persona, and system preferences in one Markdown block.
    """
    name = "identity/update_identity"
    config_class = IdentityConfig

    async def execute(self, bio: str) -> str:
        try:
            MemoryManager.update_profile_static({"bio": bio})
            return "Identity and preferences updated successfully."
        except Exception as e:
            return f"Error: {e}"

    def format_output(self, result: Any) -> str:
        if result.startswith("Error"):
            return f"[Tool Result] ⚠️ {result}"
        return f"[Tool Result] 📝 {result}"

    async def healthcheck(self) -> tuple[bool, str]: return True, "OK"
