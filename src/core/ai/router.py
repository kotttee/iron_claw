from dotenv import load_dotenv, get_key
import os
import json
import inspect

from ..providers import provider_factory
from ..context_manager import ContextManager
from ..plugin_manager import get_all_plugins
from .identity_manager import IdentityManager
from .schedule_manager import SchedulerManager
from src.core.paths import CONFIG_PATH

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
        self.scheduler_manager = SchedulerManager()
        self.provider, self.model_name = self._initialize_provider()
        self.plugin_manager = get_all_plugins(router=self)
        self.system_prompt = self._build_system_prompt()
        self.active_channels = []

    def register_channel(self, channel):
        """
        Registers an active channel instance with the router.
        """
        if channel not in self.active_channels:
            self.active_channels.append(channel)
            print(f"Router: Registered channel {channel.name}")

    def _initialize_provider(self):
        """Initializes the LLM provider from config.json."""
        if not CONFIG_PATH.exists():
            raise ValueError(f"Configuration file not found at {CONFIG_PATH}. Please run the setup.")
        
        try:
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            llm_config = config.get("llm")
            if not llm_config:
                raise ValueError("LLM configuration is missing in config.json. Please run the setup.")

            provider_name = llm_config.get("provider_name")
            api_key = llm_config.get("api_key")
            model_name = llm_config.get("model")

            if not all([provider_name, api_key, model_name]):
                raise ValueError("Provider name, API key, or model is missing from LLM configuration. Please run the setup.")

            provider = provider_factory.create_provider(provider_name, api_key)
            return provider, model_name

        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise ValueError(f"Failed to load or parse configuration: {e}. Please run the setup.")

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
                    if hasattr(tool_plugin, 'description') and tool_plugin.description:
                        tool_definitions.append(f"- {tool_plugin.name}: {tool_plugin.description.strip()}")
                    else:
                        # Fallback for functional tools or others if description is missing
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

    def get_preferred_output_channel(self):
        """
        Determines the preferred output channel based on active channels.
        Returns the channel instance and target.
        """
        # Default to console
        console_channel = next((c for c in self.active_channels if c.name == 'console'), None)

        # Check for a network channel like Telegram, which is preferred
        for channel in self.active_channels:
            if channel.name == 'telegram' and channel.is_enabled():
                admin_id = get_key(os.environ.get("ENV_PATH", ".env"), "TELEGRAM_ADMIN_ID")
                if admin_id:
                    return channel, admin_id
        
        return console_channel, None


    def handle_scheduled_event(self, event_instruction: str):
        """
        Handles a scheduled event by generating content and sending it to the
        preferred channel. Supports tool execution.
        """
        print(f"Handling scheduled event: {event_instruction}")
        
        system_prompt = self.system_prompt + "\n\nYou are executing a scheduled task. Follow the instructions and use tools if necessary."
        
        messages = [{"role": "user", "content": f"Scheduled Task: {event_instruction}"}]
        
        # Tool execution loop for scheduled events
        max_iterations = 5
        response_text = ""
        
        for i in range(max_iterations):
            response_text = self.provider.chat(
                model=self.model_name,
                messages=messages,
                system_prompt=system_prompt
            )
            
            messages.append({"role": "assistant", "content": response_text})
            
            tool_call = self._parse_tool_call(response_text)
            if tool_call:
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})
                
                print(f"Router (Scheduled): Executing tool '{tool_name}'")
                tool_result = self._execute_tool(tool_name, tool_args)
                
                messages.append({"role": "user", "content": f"[TOOL RESULT for {tool_name}]: {tool_result}"})
                continue
            else:
                break

        # Save the interaction to history
        self.context_manager.add_message("user", f"Scheduled Task: {event_instruction}")
        self.context_manager.add_message("assistant", response_text)

        # Send the response to the appropriate channel
        self._send_to_channel(response_text)

    def _send_to_channel(self, text: str):
        """
        Sends a message to the preferred output channel using a registered instance.
        """
        channel_instance, target = self.get_preferred_output_channel()

        if not channel_instance:
            print("Error: No active/preferred output channel found.")
            return

        if channel_instance.name == 'console':
            # Console channel might just print, or have a send_message method
            if hasattr(channel_instance, 'send_message') and callable(getattr(channel_instance, 'send_message')):
                 channel_instance.send_message(text)
            else:
                 print(f"Output (Console): {text}")
            return

        if hasattr(channel_instance, 'send_message') and callable(getattr(channel_instance, 'send_message')):
            try:
                channel_instance.send_message(text, target)
                print(f"Message sent via {channel_instance.name} to {target}.")
            except Exception as e:
                print(f"Error sending message via {channel_instance.name}: {e}")
        else:
            print(f"Could not find or use send_message on channel instance: {channel_instance.name}")


    def process_message(self, user_message: str, source: str) -> str:
        """
        Processes a user's message through the full chat pipeline, including tool execution.
        """
        if not user_message:
            return "Input cannot be empty."

        self.context_manager.add_message("user", user_message)
        
        # Tool execution loop
        max_iterations = 5
        for i in range(max_iterations):
            full_history = self.context_manager.history
            assistant_response = self.provider.chat(
                model=self.model_name,
                messages=full_history,
                system_prompt=self.system_prompt
            )

            self.context_manager.add_message("assistant", assistant_response)

            # Check for tool call
            tool_call = self._parse_tool_call(assistant_response)
            if tool_call:
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})
                
                print(f"Router: Executing tool '{tool_name}' with args {tool_args}")
                tool_result = self._execute_tool(tool_name, tool_args)
                print(f"Router: Tool result: {tool_result}")
                
                # Add tool result to context as a system message (or user message acting as system)
                self.context_manager.add_message("user", f"[TOOL RESULT for {tool_name}]: {tool_result}")
                # Continue the loop to let the LLM see the result
                continue
            else:
                # No tool call, final response
                return assistant_response

        return "Max tool execution iterations reached."

    def _parse_tool_call(self, text: str) -> dict | None:
        """
        Attempts to find and parse a JSON tool call in the text.
        """
        try:
            # Look for something that looks like {"tool": ...}
            # This is a simple heuristic; a more robust one might use regex or a real parser
            start_idx = text.find('{"tool":')
            if start_idx == -1:
                return None
            
            # Find the matching closing brace
            brace_count = 0
            for j in range(start_idx, len(text)):
                if text[j] == '{':
                    brace_count += 1
                elif text[j] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = text[start_idx:j+1]
                        return json.loads(json_str)
        except Exception:
            pass
        return None

    def _execute_tool(self, tool_name: str, args: dict) -> str:
        """
        Finds and executes the specified tool.
        """
        enabled_tools = [p for p in self.plugin_manager.get("tools", []) if p.is_enabled()]
        tool = next((t for t in enabled_tools if t.name == tool_name), None)
        
        if not tool:
            return f"Error: Tool '{tool_name}' not found or not enabled."

        try:
            # If it's a BaseTool (class-based), it has an execute method
            if hasattr(tool, 'execute') and callable(tool.execute):
                return str(tool.execute(**args))
            # Fallback for functional tools (already wrapped in plugin_manager.py)
            elif hasattr(tool, 'run') and callable(tool.run):
                 return str(tool.run(**args))
            else:
                return f"Error: Tool '{tool_name}' is not executable."
        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"
