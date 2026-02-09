import asyncio
import json
import signal
from datetime import datetime
from rich.console import Console
from src.core.ai.router import Router
from src.core.plugin_manager import get_all_plugins
from src.core.interfaces import BaseChannel, BaseComponent
from src.core.scheduler.manager import CoreScheduler

console = Console()

class Daemon:
    def __init__(self):
        console.print("[bold cyan]Daemon: Initializing...[/bold cyan]")
        self.router = Router()
        self.scheduler = CoreScheduler(self.router)
        self.router.scheduler = self.scheduler
        self.plugin_manager = self.router.plugin_manager
        self.running_tasks = []
        self._shutdown_event = asyncio.Event()

    async def handle_ipc_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        source_id = f"ipc_{addr[0]}_{addr[1]}"
        try:
            while True:
                data = await reader.readline()
                if not data: break
                message = data.decode().strip()
                asyncio.create_task(self.router.process_message(message, source=source_id, writer=writer))
        except Exception as e:
            console.print(f"[dim]IPC Error ({source_id}): {e}[/dim]")
        finally:
            writer.close()
            await writer.wait_closed()

    async def _run_scheduler_loop(self, scheduler: BaseComponent):
        console.print(f"[blue]Daemon: Starting scheduler '{scheduler.name}'[/blue]")
        
        while not self._shutdown_event.is_set():
            # Determine sleep duration strictly from config
            sleep_duration = None
            
            # 1. Check for Cron
            if hasattr(scheduler.config, 'cron') and scheduler.config.cron:
                try:
                    from croniter import croniter
                    now = datetime.now()
                    it = croniter(scheduler.config.cron, now)
                    next_run = it.get_next(datetime)
                    sleep_duration = (next_run - now).total_seconds()
                except ImportError:
                    console.print(f"[red]Error: 'croniter' not installed. Cannot run cron scheduler '{scheduler.name}'.[/red]")
                    return
                except Exception as e:
                    console.print(f"[red]Invalid cron expression for '{scheduler.name}': {e}[/red]")
                    return
            
            # 2. Check for Interval
            elif hasattr(scheduler.config, 'interval_seconds') and scheduler.config.interval_seconds:
                sleep_duration = scheduler.config.interval_seconds
            
            # 3. No valid config found
            if sleep_duration is None:
                console.print(f"[bold red]Error: Scheduler '{scheduler.name}' has no valid cron or interval configuration. Stopping.[/bold red]")
                return

            try:
                # Wait for the next execution or shutdown
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=max(0.1, sleep_duration))
                if self._shutdown_event.is_set():
                    break
            except asyncio.TimeoutError:
                # Time to run the iteration
                try:
                    await scheduler.run_iteration(self.router)
                except Exception as e:
                    console.print(f"[red]Scheduler '{scheduler.name}' execution error: {e}[/red]")

    async def start(self):
        console.print("[bold green]Daemon: Starting services...[/bold green]")
        ipc_server = await asyncio.start_server(self.handle_ipc_client, '127.0.0.1', 8989)
        self.running_tasks.append(asyncio.create_task(ipc_server.serve_forever()))
        
        # Запуск системного планировщика
        await self.scheduler.start()

        for cat in ["channels", "schedulers"]:
            for component in self.plugin_manager.get(cat, []):
                if not component.config.enabled:
                    console.print(f"[dim]Daemon: Skipping disabled component '{component.name}'[/dim]")
                    continue
                    
                is_healthy, msg = await component.healthcheck()
                if is_healthy:
                    if cat == "channels":
                        self.router.register_channel(component)
                        self.running_tasks.append(asyncio.create_task(component.start(self.router)))
                    else:
                        self.running_tasks.append(asyncio.create_task(self._run_scheduler_loop(component)))

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._shutdown_event.set)

        await self._shutdown_event.wait()
        await self.stop()

    async def stop(self):
        console.print("[bold yellow]Daemon: Shutting down...[/bold yellow]")
        for task in self.running_tasks:
            task.cancel()
        
        for cat in self.plugin_manager.values():
            for component in cat:
                try: component.shutdown()
                except: pass
        
        self.router.memory.shutdown()
        console.print("[bold green]Daemon: Shutdown complete.[/bold green]")
