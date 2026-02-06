from dotenv import load_dotenv, get_key
import os
import json
import inspect
from rich.console import Console

from ..providers import provider_factory
from ..context_manager import ContextManager
from ..plugin_manager import get_all_plugins
from .identity_manager import IdentityManager
from .schedule_manager import SchedulerManager
from src.core.paths import CONFIG_PATH

# Load environment variables from .env file
load_dotenv()

console = Console()

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
        self.last_channel_name = None

    def register_channel(self, channel):
        """
        Registers an active channel instance with the router.
        """
        if channel not in self.active_channels:
            self.active_channels.append(channel)
            console.print(f"Router: Registered channel {channel.name}")

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
                    executable = None
                    if hasattr(tool_plugin, 'execute') and callable(tool_plugin.execute):
                        executable = tool_plugin.execute
                    elif hasattr(tool_plugin, 'run') and callable(tool_plugin.run):
                        executable = tool_plugin.run

                    if executable:
                        docstring = inspect.getdoc(executable) or "No description available."
                        sig = inspect.signature(executable)
                        
                        arg_details = []
                        for param in sig.parameters.values():
                            if param.name == 'self': continue
                            detail = f"{param.name}"
                            if param.annotation != inspect.Parameter.empty:
                                detail += f": {param.annotation.__name__}"
                            if param.default != inspect.Parameter.empty:
                                detail += f" (default: {param.default})"
                            arg_details.append(detail)
                        
                        args_str = ", ".join(arg_details)
                        tool_definitions.append(f"- {tool_plugin.name}({args_str}): {docstring.strip()}")

                except Exception as e:
                    console.print(f"[yellow]Could not generate definition for tool {tool_plugin.name}: {e}[/yellow]")

        if tool_definitions:
            tools_prompt = "\n\n=== AVAILABLE TOOLS ===\n"
            tools_prompt += "You have access to the following Python functions. To use them, you MUST respond with a JSON object like this: {\"tool\": \"<tool_name>\", \"args\": {\"<arg_name>\": \"<value>\"}}. The 'tool' key must contain the name of the tool to use, and the 'args' key must contain a dictionary of arguments for the tool.\n\n"
            tools_prompt += "\n".join(tool_definitions)
            return base_prompt + tools_prompt
        
        return base_prompt

    def get_output_channel(self, source: str | None = None):
        """
        Determines the output channel. Prefers the source channel, then the last used channel,
        then the default preferred channel.
        """
        target_channel_name = source or self.last_channel_name
        
        if target_channel_name:
            channel_instance = next((c for c in self.active_channels if c.name == target_channel_name), None)
            if channel_instance:
                if channel_instance.name == 'telegram_bot':
                    admin_id = get_key(os.environ.get("ENV_PATH", ".env"), "TELEGRAM_ADMIN_ID")
                    if admin_id:
                        return channel_instance, admin_id
                else: # console or other simple channels
                    return channel_instance, None

        # Fallback to preferred channel if specific one not found or not usable
        return self.get_preferred_output_channel()

    def get_preferred_output_channel(self):
        """
        Determines the default preferred output channel (e.g., a network channel over console).
        """
        for channel in self.active_channels:
            if channel.name == 'telegram_bot' and channel.is_enabled():
                admin_id = get_key(os.environ.get("ENV_PATH", ".env"), "TELEGRAM_ADMIN_ID")
                if admin_id:
                    return channel, admin_id
        
        # Default to console if no other preference matches
        return next((c for c in self.active_channels if c.name == 'console'), None), None


    def handle_scheduled_event(self, event_instruction: str):
        """
        Handles a scheduled event by generating content and sending it to the
        preferred channel. Supports tool execution.
        """
        console.print(f"Handling scheduled event: {event_instruction}")
        
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
                
                console.print(f"Router (Scheduled): Executing tool '{tool_name}'")
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

    def _send_to_channel(self, text: str, source: str | None = None):
        """
        Sends a message to the appropriate output channel using a registered instance.
        """
        channel_instance, target = self.get_output_channel(source)

        if not channel_instance:
            console.print("[bold red]Error: No active output channel found to send message.[/bold red]")
            return

        console.print(f"Router: Sending message to {channel_instance.name} (target: {target or 'default'})")
        
        try:
            channel_instance.send_message(text, target)
            console.print(f"Message sent successfully via {channel_instance.name}.")
        except Exception as e:
            console.print(f"[bold red]Error sending message via {channel_instance.name}: {e}[/bold red]")


    def process_message(self, user_message: str, source: str) -> None:
        """
        Processes a user's message through the full chat pipeline, including tool execution.
        """
        self.last_channel_name = source
        if not user_message:
            self._send_to_channel("Input cannot be empty.", source)
            return

        self.context_manager.add_message("user", user_message)
        
        max_iterations = 5
        for i in range(max_iterations):
            full_history = self.context_manager.history
            console.print(f"full history len: {full_history}")
            assistant_response = self.provider.chat(
                model=self.model_name,
                messages=full_history,
                system_prompt=self.system_prompt
            )

            self.context_manager.add_message("assistant", assistant_response)

            tool_call = self._parse_tool_call(assistant_response)
            if tool_call:
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})
                
                console.print(f"Router: Executing tool '{tool_name}' with args {tool_args}")
                tool_result = self._execute_tool(tool_name, tool_args)
                console.print(f"Router: Tool result: {tool_result}")
                
                self.context_manager.add_message("user", f"[TOOL RESULT for {tool_name}]: {tool_result}")
                continue
            else:
                self._send_to_channel(assistant_response, source)
                return

        # If the loop completes, it means we've hit the max iterations
        error_injection = "[SYSTEM NOTE: You have been unable to complete the user's request because you are stuck in a loop of calling tools. Apologize to the user, explain that you have encountered an internal error, and ask them to try rephrasing their request.]"
        self.context_manager.add_message("user", error_injection)
        
        final_response = self.provider.chat(
            model=self.model_name,
            messages=self.context_manager.history,
            system_prompt=self.system_prompt
        )
        self._send_to_channel(final_response, source)


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
