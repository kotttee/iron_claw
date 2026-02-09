from src.core.interfaces import BaseTool
from src.core.ai.memory import MemoryManager
from .config import MemoryToolConfig

class AddFactTool(BaseTool[MemoryToolConfig]):
    """
    Adds a long-term fact about the user or the world to the AI's memory.
    """
    name = "memory/add_fact"
    config_class = MemoryToolConfig

    async def execute(self, fact: str) -> str:
        try:
            MemoryManager.add_fact_static(fact)
            return f"Fact remembered: {fact}"
        except Exception as e:
            return f"Error: {e}"

    async def healthcheck(self): return True, "OK"

class ClearHistoryTool(BaseTool[MemoryToolConfig]):
    """
    Clears the short-term chat history. Use this if the context is getting cluttered.
    """
    name = "memory/clear_history"
    config_class = MemoryToolConfig

    async def execute(self) -> str:
        try:
            MemoryManager.clear_history_static()
            return "Chat history cleared."
        except Exception as e:
            return f"Error: {e}"

    async def healthcheck(self): return True, "OK"
