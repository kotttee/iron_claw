from dotenv import load_dotenv
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

    @property
    def system_prompt(self) -> str:
        """
        Constructs the full system prompt dynamically, including identity and available tools.
        This is a property to ensure the prompt is rebuilt on every access,
        capturing any changes to identity files.
        """
        base_prompt = IdentityManager.get_identity_prompt()
        
        tool_definitions = []
        enabled_tools = [p for p in self.plugin_manager.get("tools", []) if p.is_enabled()]

        if enabled_tools:
            for tool_plugin in enabled_tools:
                try:
                    executable = None
                    try:
                        executable = tool_plugin.execute
                    except AttributeError:
                        executable = tool_plugin.run

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
            tools_prompt += "You have access to the following tools. If you need to use a tool, your response MUST be a JSON object with two keys: 'tool' and 'args'. The 'tool' key specifies the tool name, and the 'args' key provides the arguments as a dictionary. Your response must contain ONLY the JSON object and nothing else.\n"
            tools_prompt += "Example of a valid tool call:\n"
            tools_prompt += "{\"tool\": \"create_file\", \"args\": {\"filename\": \"test.txt\", \"content\": \"Hello World\"}}\n\n"
            tools_prompt += "Here are the tools available to you:\n"
            tools_prompt += "\n".join(tool_definitions)
            return base_prompt + tools_prompt
        
        return base_prompt

    def get_output_channel(self, source: str | None = None):
        """
        Determines the output channel based on a priority system.
        Priority: Source Channel > Last Used Channel > Preferred (Network) Channel > Console
        """
        # 1. Try the source channel first
        target_channel_name = source
        if target_channel_name:
            channel = next((c for c in self.active_channels if c.name == target_channel_name), None)
            if channel:
                target = get_key(os.environ.get("ENV_PATH", ".env"), "TELEGRAM_ADMIN_ID") if channel.name == 'telegram_bot' else None
                return channel, target

        # 2. Fallback to the last used channel
        if self.last_channel_name:
            channel = next((c for c in self.active_channels if c.name == self.last_channel_name), None)
            if channel:
                target = os.environ.get("TELEGRAM_ADMIN_ID") if channel.name == 'telegram_bot' else None
                return channel, target

        # 3. Fallback to a preferred network channel
        for channel in self.active_channels:
            if channel.name == 'telegram_bot' and channel.is_enabled():
                admin_id =  os.environ.get("TELEGRAM_ADMIN_ID")
                if admin_id:
                    return channel, admin_id
        
        # 4. Default to console if nothing else is available
        console_channel = next((c for c in self.active_channels if c.name == 'console'), None)
        return console_channel, None


    def handle_scheduled_event(self, event_instruction: str):
        """
        Handles a scheduled event by generating content and sending it to the
        preferred channel. Supports tool execution and maintains context.
        """
        console.print(f"Router: Handling scheduled event: {event_instruction}")

        self.context_manager.add_message("user", f"Scheduled Task: {event_instruction}")

        max_iterations = 5
        final_response = "Max tool execution iterations reached for scheduled event."

        for i in range(max_iterations):
            current_messages = self.context_manager.messages
            
            system_prompt = self.system_prompt + "\n\nYou are executing a scheduled task. Follow the instructions and use tools if necessary."

            assistant_response = self.provider.chat(
                model=self.model_name,
                messages=current_messages,
                system_prompt=system_prompt
            )

            self.context_manager.add_message("assistant", assistant_response)

            tool_call = self._parse_tool_call(assistant_response)
            if tool_call:
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})
                
                tool_message = f"🤖 Calling tool: `{tool_name}` with arguments: `{tool_args}`"
                self._send_to_channel(tool_message)
                
                console.print(f"Router (Scheduled): Executing tool '{tool_name}' with args {tool_args}")
                raw_result, formatted_result = self._execute_tool(tool_name, tool_args)
                console.print(f"Router (Scheduled): Tool result: {raw_result}")
                
                self.context_manager.add_message("user", f"[TOOL RESULT for {tool_name}]: {raw_result}")
                self._send_to_channel(formatted_result)
                continue
            else:
                final_response = assistant_response
                break

        self._send_to_channel(final_response)


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
        final_response = "Max tool execution iterations reached."
        for i in range(max_iterations):
            current_messages = self.context_manager.messages
            
            assistant_response = self.provider.chat(
                model=self.model_name,
                messages=current_messages,
                system_prompt=self.system_prompt
            )

            self.context_manager.add_message("assistant", assistant_response)

            tool_call = self._parse_tool_call(assistant_response)
            if tool_call:
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})
                
                tool_message = f"🤖 Calling tool: `{tool_name}` with arguments: `{tool_args}`"
                self._send_to_channel(tool_message, source)

                console.print(f"Router: Executing tool '{tool_name}' with args {tool_args}")
                raw_result, formatted_result = self._execute_tool(tool_name, tool_args)
                console.print(f"Router: Tool result: {raw_result}")
                
                self.context_manager.add_message("user", f"[TOOL RESULT for {tool_name}]: {raw_result}")
                self._send_to_channel(formatted_result, source)
                continue
            else:
                final_response = assistant_response
                break
        
        self._send_to_channel(final_response, source)


    def _parse_tool_call(self, text: str) -> dict | None:
        """
        Attempts to find and parse a JSON tool call in the text.
        """
        try:
            start_idx = text.find('{"tool":')
            if start_idx == -1:
                return None
            
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

    def _execute_tool(self, tool_name: str, args: dict) -> (str, str):
        """
        Finds and executes the specified tool.

        Returns:
            A tuple containing:
            - str: The raw, complete result of the tool execution.
            - str: A formatted, user-friendly summary of the result.
        """
        enabled_tools = [p for p in self.plugin_manager.get("tools", []) if p.is_enabled()]
        tool = next((t for t in enabled_tools if t.name == tool_name), None)
        
        if not tool:
            error_message = f"Error: Tool '{tool_name}' not found or not enabled."
            return error_message, error_message

        try:
            # 1. Execute the tool to get the raw result
            raw_result = tool.execute(**args)

            # 2. Format the output for the user
            try:
                formatted_result = tool.format_output(raw_result)
            except:
                formatted_result = "tool was called but result cant be formatted."

            return str(raw_result), str(formatted_result)

        except Exception as e:
            error_message = f"Error executing tool '{tool_name}': {e}"
            return error_message, error_message
