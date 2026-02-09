import asyncio
import os
import shutil
import subprocess
import tempfile
import time
import sys
from pathlib import Path

import questionary
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from src.core.ai.router import Router
from src.core.daemon import Daemon
from src.core.paths import DATA_ROOT, BASE_DIR, ENV_PATH
from src.core.ai.onboarding import run_onboarding_session
from src.core.ai.settings import SettingsManager

app = typer.Typer(
    name="ironclaw",
    help="A modular, open-source AI Agent Platform.",
    add_completion=False,
)
console = Console()

PID_DIR = Path(tempfile.gettempdir())
PID_FILE = PID_DIR / "iron_claw.pid"

def is_running():
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text())
        os.kill(pid, 0)
    except (ValueError, OSError):
        return False
    return True

@app.command()
def start(
    daemon: bool = typer.Option(False, "-d", "--daemon", help="Run the agent as a background daemon.")
):
    """Starts the IronClaw Daemon."""
    if is_running():
        console.print("[bold yellow]IronClaw agent is already running.[/bold yellow]")
        raise typer.Exit()

    settings = SettingsManager()
    if not settings.is_provider_configured():
        console.print("[bold yellow]IronClaw is not configured yet. You need to set up an LLM provider first.[/bold yellow]")
        if questionary.confirm("Would you like to run the setup wizard now?").ask():
            settings.run_full_setup()
            if not settings.is_provider_configured():
                console.print("[bold red]Setup was not completed. Cannot start daemon.[/bold red]")
                raise typer.Exit(1)
        else:
            console.print("Please run [bold]ironclaw config[/bold] or [bold]ironclaw onboard[/bold] to set up the agent.")
            raise typer.Exit()

    if daemon:
        console.print(Panel("🚀 [bold green]Starting IronClaw Daemon in background[/bold green]"))
        try:
            log_dir = DATA_ROOT / "logs"
            log_dir.mkdir(exist_ok=True)
            with open(log_dir / "stdout.log", "w") as stdout_log, open(log_dir / "stderr.log", "w") as stderr_log:
                p = subprocess.Popen(
                    [sys.executable, "-m", "src.console.cli", "start"],
                    close_fds=True, start_new_session=True,
                    stdout=stdout_log, stderr=stderr_log, stdin=subprocess.DEVNULL,
                )
            with open(PID_FILE, "w") as f:
                f.write(str(p.pid))
            console.print(f"Daemon started with PID: {p.pid}")
        except Exception as e:
            console.print(f"[bold red]Failed to start daemon: {e}[/bold red]")
            raise typer.Exit(1)
        raise typer.Exit()
    else:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        
        console.print(Panel("🚀 [bold green]Starting IronClaw Daemon[/bold green]"))
        try:
            d = Daemon()
            asyncio.run(d.start())
        except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
            console.print("\n[bold yellow]Daemon shutdown gracefully.[/bold yellow]")
        except Exception as e:
            console.print(f"[bold red]An error occurred: {e}[/bold red]")
            raise typer.Exit(1)
        finally:
            if PID_FILE.exists():
                PID_FILE.unlink()

@app.command()
def stop():
    """Stops the running IronClaw daemon."""
    if not PID_FILE.exists():
        console.print("[bold yellow]IronClaw daemon is not running.[/bold yellow]")
        raise typer.Exit()

    try:
        pid = int(PID_FILE.read_text())
        os.kill(pid, 15)
        console.print("[bold green]Waiting for daemon to stop...[/bold green]")
        time.sleep(2)
        if is_running():
             os.kill(pid, 9)
        
        if PID_FILE.exists():
            PID_FILE.unlink()
        console.print("[bold green]IronClaw daemon stopped.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Failed to stop daemon: {e}[/bold red]")
        raise typer.Exit(1)

@app.command()
def talk():
    """Connects to the running daemon for a direct chat session."""
    async def talk_client():
        if not is_running():
            console.print("[bold red]Error: IronClaw daemon is not running.[/bold red]")
            return

        console.print(Panel("IronClaw Terminal | Type 'stop' to cancel agent task", title="[bold green]🗣️ Live Chat[/bold green]"))
        try:
            reader, writer = await asyncio.open_connection('127.0.0.1', 8989)
            
            async def listen_for_responses():
                try:
                    while True:
                        data = await reader.read(4096)
                        if not data: break
                        response = data.decode().strip()
                        if response:
                            console.print(Markdown(response))
                            console.print("") # New line after response
                except Exception as e:
                    console.print(f"[dim]Connection closed: {e}[/dim]")

            asyncio.create_task(listen_for_responses())

            while True:
                user_input = await asyncio.to_thread(console.input, "You > ")
                if not user_input.strip(): continue
                writer.write((user_input + '\n').encode())
                await writer.drain()
        except Exception as e:
            console.print(f"[bold red]Connection lost: {e}[/bold red]")

    try:
        asyncio.run(talk_client())
    except KeyboardInterrupt:
        pass

@app.command()
def onboard():
    """Starts the onboarding process."""
    run_onboarding_session()

@app.command()
def config():
    """Interactive configuration menu."""
    try:
        # Initialize router to load plugins for the config menu
        r = Router()
        SettingsManager(router=r).run_main_menu()
    except Exception as e:
        console.print(f"[bold red]Error loading configuration menu: {e}[/bold red]")


@app.command()
def update():
    """Updates the IronClaw platform to the latest version from Git."""
    console.print(Panel("[bold blue]🔄 IronClaw Update System[/bold blue]"))

    try:
        console.print("Checking for remote changes...")
        # Выполняем git pull для обновления кода
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, check=True)

        if "Already up to date" in result.stdout:
            console.print("[green]✅ You are already on the latest version.[/green]")
        else:
            console.print(f"[bold green]🚀 Successfully updated![/bold green]")
            console.print(f"[dim]{result.stdout}[/dim]")
            console.print("\n[yellow]Please restart the Daemon to apply changes.[/yellow]")

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ Git update failed:[/bold red]\n{e.stderr}")
    except FileNotFoundError:
        console.print("[bold red]❌ Error: Git is not installed or not found in PATH.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]❌ An unexpected error occurred: {e}[/bold red]")


@app.command()
def restart(
        daemon: bool = typer.Option(True, "-d", "--daemon", help="Restart as a background daemon.")
):
    """Restarts the IronClaw daemon."""
    console.print(Panel("🔄 [bold blue]Restarting IronClaw[/bold blue]"))

    if is_running():
        try:
            stop()
        except typer.Exit:
            # Игнорируем выход из команды stop, чтобы продолжить запуск
            pass

    # Небольшая пауза, чтобы порты и файлы успели освободиться
    time.sleep(1)
    start(daemon=daemon)



if __name__ == "__main__":
    app()
