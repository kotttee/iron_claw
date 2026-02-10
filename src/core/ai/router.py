import asyncio
import os
import json
import inspect
from datetime import datetime
from typing import Optional, Any, Dict, List, Tuple
from rich.console import Console
from dotenv import load_dotenv

from ..providers import provider_factory
from ..plugin_manager import get_all_plugins
from .memory import MemoryManager
from src.core.paths import CONFIG_PATH

load_dotenv()
console = Console()

class Router:
    def __init__(self):
        self.memory = MemoryManager()
        self.scheduler = None # Будет установлен Демоном
        self.provider, self.model_name = self._initialize_provider()
        self.plugin_manager = get_all_plugins(router=self)
        self.active_channels = []
        
        self.is_busy = False
        self.current_task: Optional[asyncio.Task] = None
        self.ipc_writers: Dict[str, asyncio.StreamWriter] = {}
        # Map source/channel to specific target IDs (e.g., Telegram chat IDs)
        self.active_targets: Dict[str, str] = {}

    def register_channel(self, channel):
        if channel not in self.active_channels:
            self.active_channels.append(channel)

    def _initialize_provider(self):
        if not CONFIG_PATH.exists():
            raise ValueError("Config not found.")
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        llm = config.get("llm", {})
        provider = provider_factory.create_provider(llm.get("provider_name"), llm.get("api_key"))
        return provider, llm.get("model")

    def reinitialize_provider(self):
        """Re-initializes the LLM provider and plugins from the current config.json."""
        self.provider, self.model_name = self._initialize_provider()
        # Refresh plugins to respect 'enabled' flags in their local configs
        self.plugin_manager = get_all_plugins(router=self)
        console.print("[bold green]Router: Provider and plugins re-initialized.[/bold green]")

    def build_system_prompt(self) -> str:
        # Reload config to ensure we have the latest updates from tools/onboarding
        self.memory.config = self.memory.load_config()
        profile = self.memory.config
        facts = self.memory.get_long_term_facts()
        
        prompt = "# SYSTEM CONTEXT\n"
        prompt += f"- Current Time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n"
        prompt += "\n" + profile.bio + "\n"
        
        if facts:
            prompt += "\n=== LONG-TERM FACTS ===\n" + "\n".join(f"- {f}" for f in facts)
            
        tools = self.plugin_manager.get("tools", [])
        tool_defs = []
        for t in tools:
            # Only include tools that are enabled
            if not t.config.enabled:
                continue
            doc = inspect.getdoc(t.execute) or "No description."
            sig = inspect.signature(t.execute)
            args = ", ".join([f"{p.name}" for p in sig.parameters.values() if p.name != 'self'])
            tool_defs.append(f"- {t.name}({args}): {doc}")
            
        if tool_defs:
            prompt += "\n\n=== AVAILABLE TOOLS ===\n"
            prompt += "To use a tool, respond ONLY with a JSON object: {\"tool\": \"name\", \"args\": {...}, \"message\": \"Optional explanation for the user\"}\n"
            prompt += "\n".join(tool_defs)
            
        return prompt

    async def process_message(self, user_message: str, source: str, target_id: Optional[str] = None, writer: Optional[asyncio.StreamWriter] = None) -> None:
        if writer:
            self.ipc_writers[source] = writer
        
        if target_id:
            self.active_targets[source] = target_id

        if self.is_busy:
            # 1. If user wants to stop manually
            if user_message.lower().strip() == "stop":
                if self.current_task:
                    self.current_task.cancel()
                return
            
            # 2. If it's a scheduler message, it has priority: cancel current and proceed
            if source == "scheduler":
                if self.current_task:
                    self.current_task.cancel()
                # Wait a bit for cancellation to propagate
                await asyncio.sleep(0.1)
            else:
                # 3. Normal channel: ask to send 'stop'
                await self._send_to_channel("⏳ I am currently busy. Type 'stop' to cancel the current task.", source)
                return

        self.current_task = asyncio.create_task(self._run_chat_loop(user_message, source))
        try:
            await self.current_task
        except asyncio.CancelledError:
            await self._send_to_channel("🛑 Task Interrupted.", source)
        except Exception as e:
            await self._send_to_channel(f"❌ Error: {e}", source)
        finally:
            self.is_busy = False
            self.current_task = None

    async def _run_chat_loop(self, user_message: str, source: str):
        self.is_busy = True
        self.memory.add_message("user", user_message)
        
        max_iterations = 100
        max_errors = 5
        error_count = 0
        limit_reached = False

        for i in range(max_iterations):
            messages = self.memory.get_short_term_context()
            
            response = await asyncio.to_thread(
                self.provider.chat,
                model=self.model_name,
                messages=messages,
                system_prompt=self.build_system_prompt()
            )
            
            self.memory.add_message("assistant", response)
            tool_call = self._parse_tool_call(response)
            
            if tool_call:
                t_name, t_args = tool_call.get("tool"), tool_call.get("args", {})
                t_msg = tool_call.get("message")
                if t_msg:
                    await self._send_to_channel(f"🤖 {t_msg}", source)
                else:
                    await self._send_to_channel(f"🤖 Calling tool: `{t_name}`", source)
                res, fmt = await self._execute_tool(t_name, t_args)
                
                if fmt.startswith("Error:"):
                    error_count += 1
                
                self.memory.add_message("user", f"[TOOL RESULT]: {res}")
                await self._send_to_channel(fmt, source)

                if error_count >= max_errors:
                    self.memory.add_message("user", "[SYSTEM]: Maximum tool errors reached. Please provide a final response to the user based on available information.")
                    limit_reached = True
                    break
                
                if i == max_iterations - 1:
                    self.memory.add_message("user", "[SYSTEM]: Maximum tool iterations reached. Please provide a final response to the user.")
                    limit_reached = True
            else:
                await self._send_to_channel(response.strip(), source)
                return

        if limit_reached:
            messages = self.memory.get_short_term_context()
            final_response = await asyncio.to_thread(
                self.provider.chat,
                model=self.model_name,
                messages=messages,
                system_prompt=self.build_system_prompt()
            )
            self.memory.add_message("assistant", final_response)
            await self._send_to_channel(final_response.strip(), source)

    async def _execute_tool(self, name, args):
        tool = next((t for t in self.plugin_manager.get("tools", []) if t.name == name), None)
        if not tool or not tool.config.enabled:
            return "Tool not found or disabled", "Error: Tool not found or disabled"
        try:
            res = await tool.execute(**args)
            return str(res), tool.format_output(res)
        except Exception as e:
            return str(e), f"Error: {e}"

    def _parse_tool_call(self, text):
        """Improved parser that handles Markdown blocks and conversational noise."""
        text = text.strip()
        # Remove markdown code blocks if the AI wrapped the JSON
        if "```" in text:
            # Try to extract content between ```json and ``` or just ``` and ```
            import re
            match = re.search(r"```\S*\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                text = match.group(1)

        try:
            # Find the first '{' and last '}' to isolate the JSON object
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                return json.loads(text[start:end+1], strict=False)
        except: pass
        return None

    async def _send_to_channel(self, text: str, source: str):
        # If source is scheduler, broadcast to all active targets/channels
        if source == "scheduler":
            sent_somewhere = False
            
            # 1. Send to all active targets (e.g. last Telegram chat, last Discord channel)
            for target_source, target_id in self.active_targets.items():
                channel = next((c for c in self.active_channels if c.name == target_source), None)
                if channel:
                    await channel.send_message(text, target_id)
                    sent_somewhere = True
            
            # 2. Send to all IPC writers (Console/CLI)
            for s, writer in list(self.ipc_writers.items()):
                try:
                    writer.write((text + "\n\n").encode())
                    await writer.drain()
                    sent_somewhere = True
                except:
                    del self.ipc_writers[s]
            
            # 3. Fallback to console if nothing else is active
            if not sent_somewhere:
                channel = next((c for c in self.active_channels if c.name == "console"), None)
                if channel:
                    await channel.send_message(text, None)
            return

        # Handle IPC/Console directly if applicable
        if source.startswith("ipc_") or source == "console":
            writer = self.ipc_writers.get(source)
            if writer:
                try:
                    writer.write((text + "\n\n").encode())
                    await writer.drain()
                    return
                except:
                    del self.ipc_writers[source]

        # Find the registered channel
        channel = next((c for c in self.active_channels if c.name == source), None)
        if not channel:
            # Fallback to console if source channel not found
            channel = next((c for c in self.active_channels if c.name == "console"), None)
        
        if channel:
            target = self.active_targets.get(source)
            await channel.send_message(text, target)
