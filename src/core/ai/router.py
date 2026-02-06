from dotenv import load_dotenv, get_key
import os
import inspect

from ..providers import provider_factory
from ..context_manager import ContextManager
from ..plugin_manager import get_all_plugins, find_plugin
from .identity_manager import IdentityManager

# Load environment variables from .env file
load_dotenv()

class Router:
    """
    The Router is the central processing unit. It builds the system prompt,
    manages context, injects tool definitions, and routes messages to the LLM
    and appropriate output channels.
    """
    def __init__(self):
        """Initializes the Router and its components."""
        self.context_manager = ContextManager()
        self.provider = self._initialize_provider()
        self.system_prompt = self._build_system_prompt()
        self.plugin_manager = get_all_plugins()

    def _initialize_provider(self):
        """Initializes the LLM provider from .env settings."""
        provider_name = get_key(os.environ.get("ENV_PATH", ".env"), "LLM_PROVIDER_NAME")
        if not provider_name:
            raise ValueError("LLM_PROVIDER_NAME not found in .env. Please run setup.py.")

        provider_config = provider_factory.get_provider_config(provider_name)
        if not provider_config:
            raise ValueError(f"Config for '{provider_name}' not found in providers.json.")
            
        api_key_name = provider_config.get("api_key_name")
        api_key = get_key(os.environ.get("ENV_PATH", ".env"), api_key_name)
        if not api_key:
            raise ValueError(f"{api_key_name} not found in .env. Please run setup.py.")

        return provider_factory.create_provider(provider_name, api_key)

    def _build_system_prompt(self) -> str:
        """
        Constructs the full system prompt, including identity and available tools.
        """
        base_prompt = IdentityManager.get_identity_prompt()
        
        tool_definitions = []
        enabled_tools = [p for p in self.plugin_manager.get("tools", []) if p.is_enabled()]

        if enabled_tools:
            for tool_plugin in enabled_tools:
                try:
                    module = inspect.getmodule(tool_plugin)
                    if hasattr(module, 'run') and callable(module.run):
                        docstring = inspect.getdoc(module.run)
                        if docstring:
                            tool_definitions.append(f"- {tool_plugin.name}: {docstring.strip()}")
                except Exception:
                    pass

        if tool_definitions:
            tools_prompt = "\n\n=== AVAILABLE TOOLS ===\n"
            tools_prompt += "You have access to the following Python functions. To use them, you MUST respond with a JSON object like this: {\"tool\": \"<tool_name>\", \"args\": {\"<arg_name>\": \"<value>\"}}. The 'tool' key must contain the name of the tool to use, and the 'args' key must contain a dictionary of arguments for the tool.\n"
            tools_prompt += "\n".join(tool_definitions)
            return base_prompt + tools_prompt
        
        return base_prompt

    def get_preferred_output_channel(self) -> dict:
        """
        Determines the preferred output channel based on enabled plugins.
        Serves a single admin user.
        """
        telegram_plugin = find_plugin("telegram", plugin_type="channels")
        if telegram_plugin and telegram_plugin.is_enabled():
            admin_id = get_key(os.environ.get("ENV_PATH", ".env"), "TELEGRAM_ADMIN_ID")
            if admin_id:
                return {'type': 'telegram', 'target': admin_id}
        
        return {'type': 'console', 'target': None}

    def handle_scheduled_event(self, event_instruction: str):
        """
        Handles a scheduled event by generating content and sending it to the
        preferred channel.
        """
        print(f"Handling scheduled event: {event_instruction}")
        
        system_prompt = "You are executing a scheduled task. Generate a response based on the following instruction."
        
        model_name = get_key(os.environ.get("ENV_PATH", ".env"), "LLM_MODEL")
        if not model_name:
            raise ValueError("LLM_MODEL not found in .env.")

        # Generate content using the LLM
        response_text = self.provider.chat(
            model=model_name,
            messages=[{"role": "user", "content": event_instruction}],
            system_prompt=system_prompt
        )

        # Save the interaction to history
        self.context_manager.add_message("user", f"Scheduled Task: {event_instruction}")
        self.context_manager.add_message("assistant", response_text)

        # Send the response to the appropriate channel
        self._send_to_channel(response_text)

    def _send_to_channel(self, text: str):
        """
        Sends a message to the preferred output channel.
        """
        channel_info = self.get_preferred_output_channel()
        channel_type = channel_info['type']
        target = channel_info['target']

        if channel_type == 'console':
            print(f"Output (Console): {text}")
            return

        # Find the channel plugin and send the message
        channel_plugin = find_plugin(channel_type, plugin_type="channels")
        if channel_plugin and hasattr(channel_plugin, 'send_message'):
            try:
                channel_plugin.send_message(text, target)
                print(f"Message sent via {channel_type} to {target}.")
            except Exception as e:
                print(f"Error sending message via {channel_type}: {e}")
        else:
            print(f"Could not find or use channel plugin: {channel_type}")

    def process_message(self, user_message: str, source: str) -> str:
        """
        Processes a user's message through the full chat pipeline.
        """
        if not user_message:
            return "Input cannot be empty."

        self.context_manager.add_message("user", user_message)
        full_history = self.context_manager.history
        
        model_name = get_key(os.environ.get("ENV_PATH", ".env"), "LLM_MODEL")
        if not model_name:
            raise ValueError("LLM_MODEL not found in .env. Please run setup.py.")

        assistant_response = self.provider.chat(
            model=model_name,
            messages=full_history,
            system_prompt=self.system_prompt
        )

        self.context_manager.add_message("assistant", assistant_response)
        return assistant_response
