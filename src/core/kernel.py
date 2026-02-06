import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from rich.console import Console

from src.core.ai.router import Router
from src.core.scheduler import SchedulerManager
from src.core.plugin_manager import get_all_plugins
from src.interfaces.channel import BaseChannel

class Kernel:
    """
    The core of the IronClaw agent.

    This class is responsible for initializing all components (Router, Scheduler),
    running the main event loop for all active channels, and handling graceful shutdown.
    It is the central nervous system of the application.
    """

    def __init__(self, config_path: Path):
        """
        Initializes the Kernel and all its core components.
        
        Args:
            config_path: The path to the main `config.json` file.
        """
        self.console = Console()
        self.config_path = config_path
        self.config: Dict[str, Any] = self._load_config()
        
        # Initialize core components
        self.scheduler = SchedulerManager()
        self.router = Router(self.config, self.scheduler)
        
        # Start the scheduler and link it to the router
        self.scheduler.start(self.router)

    def _load_config(self) -> Dict[str, Any]:
        """Loads and validates the main JSON configuration file."""
        if not self.config_path.exists():
            self.console.print(f"[bold red]Error: Config file not found at '{self.config_path}'.[/bold red]")
            self.console.print("Please run [bold cyan]ironclaw setup[/bold cyan] first.")
            raise FileNotFoundError("Configuration file is missing.")
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.console.print(f"[bold red]Error reading or parsing config file: {e}[/bold red]")
            raise ValueError("Configuration file is corrupted or unreadable.") from e

    async def _run_main_loop(self):
        """The main asynchronous event loop that runs all enabled channels."""
        all_plugin_classes = get_all_plugins(BaseChannel, "channels")
        all_plugins = {p().plugin_id: p for p in all_plugin_classes}

        tasks = []
        enabled_channels = self.config.get("channels", {})
        if not enabled_channels:
            self.console.print("[bold yellow]Warning: No channels are enabled in the configuration.[/bold yellow]")
            return

        for plugin_id, plugin_config in enabled_channels.items():
            if plugin_class := all_plugins.get(plugin_id):
                channel_instance = plugin_class()
                self.router.register_channel(channel_instance) # Let the router know about the active channel
                tasks.append(asyncio.create_task(channel_instance.start(plugin_config, self.router)))
            else:
                self.console.print(f"[bold red]Warning: Configured plugin '{plugin_id}' not found.[/bold red]")
        
        if not tasks:
            self.console.print("[bold red]Error: No valid channels could be started.[/bold red]")
            return

        self.console.rule("[bold green]IronClaw Agent is Running[/bold green]")
        await asyncio.gather(*tasks)

    def run(self):
        """
        Starts the agent's main lifecycle. This is the primary entry point.
        It initializes, runs the main loop, and handles shutdown.
        """
        self.console.rule("[bold blue]IronClaw Kernel Initializing[/bold blue]")
        try:
            self.console.print("Agent is running... Press Ctrl+C to stop.")
            asyncio.run(self._run_main_loop())
        except KeyboardInterrupt:
            self.console.print("\n") # Move to the next line after Ctrl+C
        finally:
            self.shutdown()

    def shutdown(self):
        """Performs a graceful shutdown of all kernel components."""
        self.console.rule("[bold magenta]Kernel Shutting Down[/bold magenta]")
        self.scheduler.stop()
        self.console.print("[green]✔ Scheduler shut down gracefully.[/green]")
        self.console.print("Goodbye.")
