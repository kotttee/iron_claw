import asyncio
import inspect
from rich.console import Console
from src.core.ai.router import Router
from src.core.plugin_manager import get_all_plugins
from src.core.interfaces import ConfigurablePlugin

console = Console()

class Kernel:
    """
    The Kernel is the core of the IronClaw agent. It initializes all components,
    manages the main event loop, and orchestrates the interactions between plugins.
    """

    def __init__(self):
        """Initializes the Kernel, Router, and Plugin Manager."""
        console.print("[bold cyan]Kernel: Initializing...[/bold cyan]")
        try:
            self.router = Router()
            # Pass the router to the plugin manager so it can be injected into tools
            self.plugin_manager = get_all_plugins(router=self.router)
        except Exception as e:
            console.print(f"[bold red]Kernel Error: Failed to initialize components: {e}[/bold red]")
            raise

    async def start(self):
        """
        Performs health checks on all channels and starts the healthy ones.
        """
        console.print("[bold green]Kernel: Starting main loop...[/bold green]")
        
        if hasattr(self.router, 'scheduler_manager'):
            self.router.scheduler_manager.start(self.router)

        channel_classes = self.plugin_manager.get("channels", [])

        if not channel_classes:
            console.print("[bold yellow]Kernel Warning: No channel plugins found. Agent will be idle.[/bold yellow]")
            return

        tasks = []
        for channel_class in channel_classes:
            try:
                # Instantiate the channel class
                channel_instance = channel_class()
                
                # Only proceed with enabled channels (if they are configurable)
                if isinstance(channel_instance, ConfigurablePlugin):
                    if not channel_instance.is_enabled():
                        # Silently skip disabled plugins
                        continue
                
                # Perform health check
                is_healthy, message = await channel_instance.healthcheck()
                
                if is_healthy:
                    console.print(f"✅ [green]Healthcheck OK for channel '{channel_instance.name}': {message}[/green]")
                    self.router.register_channel(channel_instance)
                    
                    # Prepare and create the start task
                    sig = inspect.signature(channel_instance.start)
                    kwargs = {}
                    if 'config' in sig.parameters:
                        kwargs['config'] = getattr(channel_instance, 'config', {})
                    if 'router' in sig.parameters:
                        kwargs['router'] = self.router
                    
                    tasks.append(asyncio.create_task(channel_instance.start(**kwargs)))
                else:
                    console.print(f"⚠️ [yellow]Healthcheck FAILED for channel '{channel_instance.name}': {message}. Skipping...[/yellow]")

            except Exception as e:
                console.print(f"🚨 [bold red]Kernel Error: Failed to initialize or healthcheck channel {channel_class.__name__}: {e}[/bold red]")

        if tasks:
            console.print(f"[cyan]Kernel: Running {len(tasks)} healthy channel task(s). Press Ctrl+C to stop.[/cyan]")
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            console.print("[yellow]Kernel Warning: No healthy and enabled channels found to start.[/yellow]")
