import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from litellm import completion

from src.core.memory import MemoryManager
from src.core.plugin_loader import load_plugins
from src.interfaces.tool import BaseTool
from src.plugins.tools.standard.scheduler import ScheduleTaskTool

if TYPE_CHECKING:
    from src.interfaces.channel import BaseChannel
    from src.core.scheduler import SchedulerManager

# --- File Naming Standard ---
DATA_DIR = Path("data")
CONTACTS_PATH = DATA_DIR / "contacts.json"
# ... other paths from previous steps

class MessageRouter:
    """The agent's core logic, now with a contact registry and smart routing."""
    def __init__(self, config: Dict[str, Any], scheduler: "SchedulerManager"):
        self.config = config
        self.scheduler = scheduler
        self.memory_manager = MemoryManager()
        self.active_channels: Dict[str, "BaseChannel"] = {}
        self.tools = self._load_tools()
        
        llm_config = self.config.get("llm", {})
        if api_key := llm_config.get("api_key"):
            os.environ["OPENAI_API_KEY"] = api_key

    def register_channel(self, channel: "BaseChannel"):
        """Adds a running channel instance to the active registry."""
        self.active_channels[channel.plugin_id] = channel
        print(f"Channel '{channel.plugin_id}' registered.")

    def _load_tools(self) -> List[BaseTool]:
        """Loads all tools, injecting the router instance for context-aware tools."""
        tool_classes = load_plugins(BaseTool, "tools")
        loaded_tools: List[BaseTool] = []
        for cls in tool_classes:
            if issubclass(cls, ScheduleTaskTool):
                loaded_tools.append(cls(router=self))
            else:
                loaded_tools.append(cls())
        return loaded_tools

    def _update_contact_info(self, user_id: str, channel: "BaseChannel"):
        """Saves the user's last used channel and contact ID."""
        contacts = {}
        if CONTACTS_PATH.exists():
            try:
                contacts = json.loads(CONTACTS_PATH.read_text())
            except (json.JSONDecodeError, IOError):
                pass # Overwrite if corrupted
        
        # For now, we assume a single primary user
        primary_user = "default_user"
        if primary_user not in contacts:
            contacts[primary_user] = {"contacts": {}}
        
        contacts[primary_user]["last_active_plugin"] = channel.plugin_id
        contacts[primary_user]["contacts"][channel.plugin_id] = user_id # user_id is the chat_id here
        
        CONTACTS_PATH.write_text(json.dumps(contacts, indent=4))

    def get_preferred_output_channel(self, user_id: str = "default_user") -> Optional[Dict[str, str]]:
        """Gets the last active channel info for a user."""
        if not CONTACTS_PATH.exists(): return None
        try:
            contacts = json.loads(CONTACTS_PATH.read_text())
            user_data = contacts.get(user_id, {})
            last_active = user_data.get("last_active_plugin")
            if last_active and last_active in user_data.get("contacts", {}):
                return {
                    "plugin_id": last_active,
                    "user_contact_id": user_data["contacts"][last_active]
                }
        except (json.JSONDecodeError, IOError):
            return None
        return None

    async def send_outbound_message(self, content: str, plugin_id: str, user_contact_id: str):
        """Sends a message to a specific user on a specific channel."""
        if channel_instance := self.active_channels.get(plugin_id):
            await channel_instance.send_reply(user_contact_id, content)
        else:
            print(f"Error: Attempted to send message to unregistered channel '{plugin_id}'.")

    async def handle_scheduled_event(self, context: Dict[str, Any], message: str):
        """Handles a triggered event from the scheduler and routes it correctly."""
        plugin_id = context.get("plugin_id")
        user_contact_id = context.get("user_contact_id")

        if not plugin_id or not user_contact_id:
            print(f"Scheduler Error: Invalid context for scheduled event: {context}")
            return
        
        notification = f"🔔 Reminder: {message}"
        await self.send_outbound_message(notification, plugin_id, user_contact_id)

    async def route_message(self, channel: "BaseChannel", user_id: str, message_text: str):
        """Main processing loop. Now updates contact info on every message."""
        self._update_contact_info(user_id, channel)
        # The rest of the routing logic (system prompt, tool loop, etc.) remains here.
        # This code is omitted for brevity but is assumed to be the same as the previous step.
        pass
