from dotenv import load_dotenv, get_key
import os
import inspect

from .providers import provider_factory
from .context_manager import ContextManager
from .plugin_manager import get_all_plugins
from .identity import get_system_prompt

# Load environment variables from .env file
load_dotenv()

class Router:
    """
    The Router is the central processing unit. It builds the system prompt,
    manages context, injects tool definitions, and routes messages to the LLM.
    """
    def __init__(self):
        """Initializes the Router and its components."""
        self.context_manager = ContextManager()
        self.provider = self._initialize_provider()
        self.system_prompt = self._build_system_prompt()

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
        Constructs the full system prompt, including identity, user info, and available tools.
        """
        base_prompt = get_system_prompt()
        
        # --- Tool Injection ---
        tool_definitions = []
        all_plugins = get_all_plugins()
        enabled_tools = [p for p in all_plugins.get("tools", []) if p.is_enabled()]

        if enabled_tools:
            for tool_plugin in enabled_tools:
                # Dynamically get the 'run' function from the loaded module instance
                # This assumes the plugin instance has its module loaded.
                # A more robust way might be to store module path in the plugin.
                try:
                    # This is a bit of a hack; assumes the plugin class is defined in a module
                    # that has a 'run' function. A better design would be for the plugin
                    # to expose its primary function directly.
                    module = inspect.getmodule(tool_plugin)
                    if hasattr(module, 'run') and callable(module.run):
                        docstring = inspect.getdoc(module.run)
                        if docstring:
                            tool_definitions.append(f"- {tool_plugin.name}: {docstring.strip()}")
                except Exception:
                    # Could fail if module is not found, etc.
                    pass

        if tool_definitions:
            tools_prompt = "\n\n=== AVAILABLE TOOLS ===\n"
            tools_prompt += "You have access to the following Python functions. To use them, you MUST respond with a JSON object like this: {\"tool\": \"<tool_name>\", \"args\": {\"<arg_name>\": \"<value>\"}}. The 'tool' key must contain the name of the tool to use, and the 'args' key must contain a dictionary of arguments for the tool.\n"
            tools_prompt += "\n".join(tool_definitions)
            return base_prompt + tools_prompt
        
        return base_prompt

    def process_message(self, user_message: str, source: str) -> str:
        """
        Processes a user's message through the full chat pipeline.
        """
        if not user_message:
            return "Input cannot be empty."

        self.context_manager.add_message("user", user_message)
        # Use the in-memory history directly
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
