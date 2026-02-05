import json
import os
from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING

from litellm import completion

from src.core.memory import MemoryManager
from src.core.plugin_loader import load_plugins
from src.interfaces.tool import BaseTool

if TYPE_CHECKING:
    from src.interfaces.channel import BaseChannel
    from src.core.scheduler import SchedulerManager

# --- File Naming Standard ---
IDENTITY_DIR = Path("data/identity")
AI_IDENTITY_PATH = IDENTITY_DIR / "ai.md"
USER_IDENTITY_PATH = IDENTITY_DIR / "user.md"
MEMORY_DIR = Path("data/memory")
NOTEBOOK_PATH = MEMORY_DIR / "memory.md"

def _read_file_safe(path: Path) -> str:
    """Reads a file, returning a default message if it doesn't exist."""
    if not path.exists():
        return f"[File not found: {path.name}]"
    return path.read_text(encoding="utf-8").strip()

class MessageRouter:
    """The final version of the agent's core logic 'brain'."""
    def __init__(self, config: Dict[str, Any], scheduler: "SchedulerManager"):
        self.config = config
        self.scheduler = scheduler
        self.memory_manager = MemoryManager()
        self.tools = self._load_tools()
        
        llm_config = self.config.get("llm", {})
        if api_key := llm_config.get("api_key"):
            os.environ["OPENAI_API_KEY"] = api_key

    def _load_tools(self) -> List[BaseTool]:
        """Loads all available tool plugins."""
        # This can be expanded to inject context like the scheduler into tools
        return [cls() for cls in load_plugins(BaseTool, "tools")]

    def _construct_system_prompt(self) -> str:
        """Constructs the 'Strong System Prompt' from identity and memory files."""
        return (
            f"--- IDENTITY ---\n{_read_file_safe(AI_IDENTITY_PATH)}\n\n"
            f"--- USER INFO ---\n{_read_file_safe(USER_IDENTITY_PATH)}\n\n"
            f"--- LONG TERM MEMORY ---\n{_read_file_safe(NOTEBOOK_PATH)}\n\n"
            f"--- OPERATIONAL RULES ---\n"
            "1. You are IronClaw, running in an infinite loop. Stay in character as defined in your IDENTITY.\n"
            "2. Use your tools to interact with the system, gather information, or remember things.\n"
            "3. If a tool fails, analyze the error message and retry with a corrected approach. Do not give up.\n"
            "4. Think step-by-step. Plan your actions. Then, execute.\n"
        )

    async def route_message(self, channel: "BaseChannel", user_id: str, message_text: str):
        """The main processing loop with self-correction."""
        self.memory_manager.log_interaction("user", message_text)
        
        system_prompt = self._construct_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            *self.memory_manager.get_rolling_context(),
        ]
        
        model = self.config.get("llm", {}).get("model", "gpt-4o")
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = await completion(
                    model=model,
                    messages=messages,
                    tools=[tool.to_openai_schema() for tool in self.tools],
                )
                response_message = response.choices[0].message
                messages.append(response_message)

                if not response_message.tool_calls:
                    final_text = response_message.content or "I have completed the task."
                    self.memory_manager.log_interaction("assistant", final_text)
                    await channel.send_reply(user_id, final_text)
                    return

                # --- Tool Execution Loop ---
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_to_execute = next((t for t in self.tools if t.name == tool_name), None)
                    
                    if not tool_to_execute:
                        result = f"Error: Tool '{tool_name}' not found."
                    else:
                        try:
                            tool_args = json.loads(tool_call.function.arguments)
                            result = tool_to_execute.execute(**tool_args)
                        except Exception as e:
                            result = f"Error executing tool '{tool_name}': {e}"
                    
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_name, "content": str(result)})
                
                # If we've executed tools, loop back to the LLM for the next step
                continue

            except Exception as e:
                error_message = f"An unexpected error occurred in the router: {e}"
                self.memory_manager.log_interaction("system", error_message)
                if attempt < max_retries - 1:
                    messages.append({"role": "system", "content": f"Error on attempt {attempt + 1}: {e}. Retrying..."})
                    continue
                else:
                    await channel.send_reply(user_id, f"I'm sorry, I encountered a critical error after multiple retries: {e}")
                    return
        
        # If the loop finishes (e.g., max retries with only tool calls), send a final status.
        final_status = "I seem to be stuck in a loop. Please clarify the task."
        self.memory_manager.log_interaction("assistant", final_status)
        await channel.send_reply(user_id, final_status)
