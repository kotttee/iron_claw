import asyncio
import inspect
import json
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
            self.plugin_manager = get_all_plugins(router=self.router)
        except Exception as e:
            console.print(f"[bold red]Kernel Error: Failed to initialize components: {e}[/bold red]")
            raise

    async def handle_ipc_client(self, reader, writer):
        """Callback to handle a client connection for IPC."""
        console.print("[dim]IPC client connected.[/dim]")
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                
                message = data.decode().strip()
                console.print(f"[dim]IPC received: {message}[/dim]")
                
                # Process the message through the router, specifying 'console' as the source
                self.router.process_message(message, source="console")
                
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            console.print("[dim]IPC client disconnected.[/dim]")
            writer.close()
            await writer.wait_closed()

    async def start(self):
        """
        Performs health checks, starts channels, and runs the IPC server.
        """
        console.print("[bold green]Kernel: Starting main loop...[/bold green]")
        
        # Start the scheduler
        if hasattr(self.router, 'scheduler_manager'):
            self.router.scheduler_manager.start(self.router)

        # Start the IPC server
        ipc_server = await asyncio.start_server(
            self.handle_ipc_client, '127.0.0.1', 8989)
        console.print("[cyan]Kernel: IPC server listening on port 8989.[/cyan]")

        # Discover and start channel plugins
        channel_classes = self.plugin_manager.get("channels", [])
        tasks = [asyncio.create_task(ipc_server.serve_forever())]

        if not channel_classes:
            console.print("[bold yellow]Kernel Warning: No channel plugins found.[/bold yellow]")

        for channel_class in channel_classes:
            try:
                channel_instance = channel_class()
                if isinstance(channel_instance, ConfigurablePlugin) and not channel_instance.is_enabled():
                    continue
                
                is_healthy, message = await channel_instance.healthcheck()
                if is_healthy:
                    console.print(f"✅ [green]Healthcheck OK for channel '{channel_instance.name}': {message}[/green]")
                    self.router.register_channel(channel_instance)
                    
                    sig = inspect.signature(channel_instance.start)
                    kwargs = {'router': self.router} if 'router' in sig.parameters else {}
                    tasks.append(asyncio.create_task(channel_instance.start(**kwargs)))
                else:
                    console.print(f"⚠️ [yellow]Healthcheck FAILED for channel '{channel_instance.name}': {message}.[/yellow]")
            except Exception as e:
                console.print(f"🚨 [bold red]Error initializing channel {getattr(channel_class, '__name__', 'UnknownChannel')}: {e}[/bold red]")

        if len(tasks) > 1: # More than just the IPC server
            console.print(f"[cyan]Kernel: Running {len(tasks) - 1} channel task(s). Press Ctrl+C to stop.[/cyan]")
            await asyncio.gather(*tasks)
        else:
            console.print("[yellow]Kernel Warning: No healthy channels found. Running IPC server only.[/yellow]")
            await asyncio.gather(*tasks)
