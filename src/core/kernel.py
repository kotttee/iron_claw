import asyncio
import inspect
from rich.console import Console
from src.core.ai.router import Router
from src.core.plugin_manager import get_all_plugins

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
            self.plugin_manager = get_all_plugins()
        except Exception as e:
            console.print(f"[bold red]Kernel Error: Failed to initialize components: {e}[/bold red]")
            raise

    async def start(self):
        """
        Starts the main asynchronous loop, activating all enabled channel plugins.
        """
        console.print("[bold green]Kernel: Starting main loop...[/bold green]")
        
        # Start the scheduler
        if hasattr(self.router, 'scheduler_manager'):
            self.router.scheduler_manager.start(self.router)

        # In plugin_manager.py, we updated get_all_plugins to return class objects for channels
        channel_classes = self.plugin_manager.get("channels", [])

        if not channel_classes:
            console.print("[bold yellow]Kernel Warning: No channel plugins found. Agent will be idle.[/bold yellow]")
            return

        active_channel_instances = []
        for channel_class in channel_classes:
            try:
                # Check if it's already an instance (should be a class based on our changes)
                if not inspect.isclass(channel_class):
                    # If it's already an instance, just use it
                    instance = channel_class
                else:
                    # Pass the router instance to the channel constructor if it takes it
                    sig = inspect.signature(channel_class.__init__)
                    if 'router' in sig.parameters:
                        kwargs = {'router': self.router}
                    else:
                        kwargs = {}
                    instance = channel_class(**kwargs)


                
                if hasattr(instance, 'is_enabled') and not instance.is_enabled():
                    continue

                self.router.register_channel(instance)
                active_channel_instances.append(instance)
                console.print(f"Kernel: Initialized and registered channel '{getattr(instance, 'name', 'unknown')}'.")
                
            except Exception as e:
                console.print(f"[red]Kernel Error: Failed to create instance of {channel_class}: {e}[/red]")

        if not active_channel_instances:
            console.print("[bold red]Kernel Error: No channel instances were successfully created. Aborting.[/bold red]")
            return

        # Start all channel tasks
        tasks = []
        
        for channel in active_channel_instances:
            if hasattr(channel, 'start') and callable(channel.start):
                # Check signature of start method
                sig = inspect.signature(channel.start)
                kwargs = {}
                if 'config' in sig.parameters:
                    # Try to get config if it's a ConfigurablePlugin
                    kwargs['config'] = getattr(channel, 'config', {})
                if 'router' in sig.parameters:
                    kwargs['router'] = self.router
                
                tasks.append(asyncio.create_task(channel.start(**kwargs)))
        
        if tasks:
            console.print(f"[cyan]Kernel: Running {len(tasks)} channel task(s). Press Ctrl+C to stop.[/cyan]")
            await asyncio.gather(*tasks)
        else:
            console.print("[yellow]Kernel Warning: No startable channel tasks were found.[/yellow]")
