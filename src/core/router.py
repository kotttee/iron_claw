import json
import os
from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING

# Import the new loader
from src.core.loader import load_custom_tools
from src.core.memory import MemoryManager
from src.core.plugin_loader import load_plugins
from src.core.providers import get_provider
from src.interfaces.tool import BaseTool

if TYPE_CHECKING:
    from src.interfaces.channel import BaseChannel
    from src.core.scheduler import SchedulerManager

# ... (other path constants remain the same)

class MessageRouter:
    """The agent's core logic, now with dynamic custom tool loading."""
    def __init__(self, config: Dict[str, Any], scheduler: "SchedulerManager"):
        self.config = config
        self.scheduler = scheduler
        self.memory_manager = MemoryManager()
        
        # Initialize the provider from config
        llm_config = self.config.get("llm", {})
        self.provider = get_provider(
            provider_name=llm_config.get("provider", "openai"),
            api_key=os.environ.get(f"{llm_config.get('provider', 'openai').upper()}_API_KEY", "")
        )
        
        self.tools = self._load_tools()

    def _load_tools(self) -> Dict[str, Any]:
        """Loads all standard and custom tools."""
        # Load standard tools (assuming they are classes inheriting BaseTool)
        standard_tools = {
            tool.name: tool 
            for tool in [cls() for cls in load_plugins(BaseTool, "tools")]
        }
        
        # Load custom tools (which are standalone functions)
        custom_tools = load_custom_tools()
        
        # Merge them into a single registry
        # Note: Custom tools need a wrapper or a different execution path if they don't fit the BaseTool schema.
        # For now, we'll handle them separately in the execution logic.
        return {**standard_tools, **custom_tools}

    def _construct_system_prompt(self) -> str:
        """Constructs the system prompt, now with dynamic tool descriptions."""
        base_prompt = (
            f"--- IDENTITY ---\n{_read_file_safe(AI_IDENTITY_PATH)}\n\n"
            # ... (rest of the prompt from previous steps)
        )
        
        # --- Dynamic Tool Injection ---
        tool_descriptions = "\n--- AVAILABLE TOOLS ---\n"
        for name, tool in self.tools.items():
            if isinstance(tool, BaseTool):
                # Standard class-based tool
                description = tool.description
            else:
                # Custom function-based tool
                description = tool.__doc__
            
            tool_descriptions += f"- Tool: `{name}`\n  Description: {description.strip()}\n"
            
        return base_prompt + tool_descriptions

    async def route_message(self, channel: "BaseChannel", user_id: str, message_text: str):
        """Main processing loop with updated tool execution logic."""
        # ... (message logging and system prompt construction)

        # In the tool execution part of the loop:
        # if tool_name in self.tools:
        #     tool_to_execute = self.tools[tool_name]
        #     if isinstance(tool_to_execute, BaseTool):
        #         # Execute standard tool
        #         result = tool_to_execute.execute(**tool_args)
        #     else:
        #         # Execute custom tool (function)
        #         result = tool_to_execute(**tool_args)
        # ... (rest of the logic)
        pass # Placeholder for the full routing logic
