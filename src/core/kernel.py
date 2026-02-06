import asyncio
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
        
        channel_plugins = [
            p for p in self.plugin_manager.get("channels", []) if p.is_enabled()
        ]

        if not channel_plugins:
            console.print("[bold yellow]Kernel Warning: No enabled channel plugins found. Agent will be idle.[/bold yellow]")
            return

        active_channel_instances = []
        for plugin_module in channel_plugins:
            if hasattr(plugin_module, "name"):
                # Skip the console channel
                if plugin_module.name == "console":
                    continue

                channel_class = getattr(plugin_module, "name")
                
                # Pass the router instance to the channel constructor
                try:
                    channel_instance = channel_class(self.router)
                    self.router.register_channel(channel_instance)
                    active_channel_instances.append(channel_instance)
                    console.print(f"Kernel: Initialized and registered channel '{plugin_module.name}'.")
                except TypeError:
                    # Fallback for channels that don't need the router at init
                    try:
                        channel_instance = channel_class()
                        self.router.register_channel(channel_instance)
                        active_channel_instances.append(channel_instance)
                        console.print(f"Kernel: Initialized and registered channel '{plugin_module.name}' (without router injection).")
                    except Exception as e:
                        console.print(f"[red]Kernel Error: Failed to create instance of {plugin_module.name}: {e}[/red]")
                except Exception as e:
                    console.print(f"[red]Kernel Error: Failed to create instance of {plugin_module.name}: {e}[/red]")
            else:
                console.print(f"[red]Kernel Error: Could not find class '{plugin_module.name}' in plugin '{plugin_module.name}'.[/red]")

        if not active_channel_instances:
            console.print("[bold red]Kernel Error: No channel instances were successfully created. Aborting.[/bold red]")
            return

        # Start all channel tasks
        tasks = []
        for channel in active_channel_instances:
            if hasattr(channel, 'start') and callable(channel.start):
                tasks.append(asyncio.create_task(channel.start()))
        
        if tasks:
            console.print(f"[cyan]Kernel: Running {len(tasks)} channel task(s). Press Ctrl+C to stop.[/cyan]")
            await asyncio.gather(*tasks)
        else:
            console.print("[yellow]Kernel Warning: No startable channel tasks were found.[/yellow]")
