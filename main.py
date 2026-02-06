import asyncio
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import time
import sys

import questionary
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from src.core.ai.router import Router
from src.core.ai.onboarding import run_onboarding_session
from src.core.ai.settings import SettingsManager
from src.core.kernel import Kernel
from src.core.paths import DATA_ROOT, BASE_DIR, ENV_PATH
from src.core.plugin_manager import get_all_plugins
from src.interfaces.channel import BaseChannel

# --- App Setup ---
app = typer.Typer(
    name="ironclaw",
    help="A modular, open-source AI Agent Platform.",
    add_completion=False,
)
console = Console()

PID_DIR = Path(tempfile.gettempdir())
PID_FILE = PID_DIR / "iron_claw.pid"

# --- Global Kernel/Router Instance ---
# This allows the `talk` command to access the same context as the running agent
_kernel_instance: Kernel | None = None

def get_kernel() -> Kernel:
    """Initializes and returns a singleton Kernel instance."""
    global _kernel_instance
    if _kernel_instance is None:
        _kernel_instance = Kernel()
    return _kernel_instance

class ConsoleChannel(BaseChannel):
    """A simple channel for console interaction used by the `talk` command."""
    def __init__(self):
        super().__init__(name="console", category="channel")

    async def start(self, *args, **kwargs):
        pass # Not needed for talk command

    def send_message(self, text: str, target: str | None = None):
        console.print(Markdown(text))

    async def healthcheck(self):
        return True, "OK"


def is_running():
    """Check if the agent is running by checking the PID file."""
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text())
        os.kill(pid, 0)  # Check if the process exists
    except (ValueError, OSError):
        return False
    return True


def update_provider():
    """Starts the interactive process to update the LLM provider."""
    console.print(Panel("Provider Configuration", title="[bold cyan]Settings[/bold cyan]"))
    settings_manager = SettingsManager()
    settings_manager.configure_provider()


def configure_channels():
    """Dynamically discovers and configures communication channels."""
    console.print(Panel("Channel Configuration", title="[bold cyan]📡 Channels[/bold cyan]"))
    
    all_plugins = get_all_plugins()
    channel_classes = all_plugins.get("channels", [])
    
    configurable_channels = []
    for chan_class in channel_classes:
        instance = chan_class()
        # Exclude the 'console' channel from the list
        if hasattr(instance, 'name') and instance.name == 'console':
            continue
        if hasattr(instance, 'setup_wizard') and callable(instance.setup_wizard):
            configurable_channels.append(instance)

    if not configurable_channels:
        console.print("[yellow]No configurable external channels found.[/yellow]")
        return

    choices = [channel.name for channel in configurable_channels]
    choices.extend([questionary.Separator(), "Back"])

    choice = questionary.select(
        "Select a channel to configure:",
        choices=choices
    ).ask()

    if choice and choice != "Back":
        selected_channel = next((c for c in configurable_channels if c.name == choice), None)
        if selected_channel:
            try:
                selected_channel.setup_wizard()
                console.print("[bold yellow]A restart is required for channel changes to take effect. Use `ironclaw restart`.[/bold yellow]")
            except Exception as e:
                console.print(f"[bold red]An error occurred during {choice} setup: {e}[/bold red]")


# --- CLI Commands ---

@app.command()
def start(
    daemon: bool = typer.Option(False, "-d", "--daemon", help="Run the agent as a background daemon.")
):
    """
    Starts the agent's asynchronous main loop via the Kernel.
    """
    if is_running():
        console.print("[bold yellow]IronClaw agent is already running.[/bold yellow]")
        raise typer.Exit()

    if daemon:
        console.print(Panel("🚀 [bold green]Starting IronClaw Agent in background[/bold green]"))
        try:
            log_dir = DATA_ROOT / "logs"
            log_dir.mkdir(exist_ok=True)
            stdout_log = open(log_dir / "stdout.log", "w")
            stderr_log = open(log_dir / "stderr.log", "w")

            p = subprocess.Popen(
                [sys.executable, __file__, "start"],
                close_fds=True,
                start_new_session=True,
                stdout=stdout_log,
                stderr=stderr_log,
                stdin=subprocess.DEVNULL,
            )
            with open(PID_FILE, "w") as f:
                f.write(str(p.pid))
            console.print(f"Daemon started with PID: {p.pid}")
            raise typer.Exit()
        except Exception as e:
            console.print(f"[bold red]Failed to start daemon: {e}[/bold red]")
            raise typer.Exit(1)
    else:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        
        if os.isatty(sys.stdout.fileno()):
            console.print(Panel("🚀 [bold green]Starting IronClaw Agent[/bold green]"))
        
        try:
            kernel = get_kernel()
            asyncio.run(kernel.start())
        except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
            if os.isatty(sys.stdout.fileno()):
                console.print("\n[bold yellow]Agent shutdown gracefully.[/bold yellow]")
        except Exception as e:
            log_path = DATA_ROOT / "error.log"
            log_path.parent.mkdir(exist_ok=True)
            with open(log_path, "a") as f:
                f.write(f"{time.ctime()}: {e}\n")
            if os.isatty(sys.stdout.fileno()):
                console.print(f"[bold red]An error occurred during agent execution: {e}[/bold red]")
            raise typer.Exit(1)
        finally:
            if PID_FILE.exists():
                PID_FILE.unlink()


@app.command()
def stop():
    """Stops the running IronClaw agent daemon."""
    if not PID_FILE.exists():
        console.print("[bold yellow]IronClaw agent is not running.[/bold yellow]")
        raise typer.Exit()

    try:
        pid = int(PID_FILE.read_text())
        os.kill(pid, 15)
        console.print("[bold green]Waiting for agent to stop...[/bold green]")
        time.sleep(2)
        if is_running():
             os.kill(pid, 9)
             console.print("[bold yellow]Agent force-stopped.[/bold yellow]")
        
        if PID_FILE.exists():
            PID_FILE.unlink()
        console.print("[bold green]IronClaw agent stopped successfully.[/bold green]")

    except (ValueError, ProcessLookupError):
        console.print("[bold yellow]Agent process not found. Cleaning up stale PID file.[/bold yellow]")
        if PID_FILE.exists():
            PID_FILE.unlink()
        raise typer.Exit()
    except Exception as e:
        console.print(f"[bold red]Failed to stop agent: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def restart():
    """Restarts the IronClaw agent daemon."""
    console.print("🔄 [bold blue]Restarting IronClaw agent...[/bold blue]")
    try:
        stop()
    except typer.Exit:
        pass
    
    start(daemon=True)


@app.command()
def status():
    """Checks the status of the IronClaw agent."""
    if is_running():
        pid = int(PID_FILE.read_text())
        console.print(f"[bold green]IronClaw agent is running with PID: {pid}[/bold green]")
    else:
        console.print("[bold yellow]IronClaw agent is not running.[/bold yellow]")


@app.command()
def talk():
    """
    Starts the IronClaw terminal interface for seamless, continuous chat.
    This command uses the same underlying context as the running agent.
    """
    try:
        kernel = get_kernel()
        router = kernel.router
        
        # Ensure the console channel is registered for this session
        console_channel = ConsoleChannel()
        router.register_channel(console_channel)

    except Exception as e:
        console.print(f"[bold red]Initialization Error: {e}[/bold red]")
        console.print(
            "[yellow]Hint: Have you run the onboarding process yet? (`ironclaw onboard`)[/yellow]"
        )
        raise typer.Exit(1)

    os.system("cls" if os.name == "nt" else "clear")
    console.print(
        Panel(
            "IronClaw Terminal Interface | Press Ctrl+C to Exit",
            title="[bold green]🗣️ Live Chat[/bold green]",
            expand=False,
        )
    )
    
    # Display recent history
    console.print("[dim]... recent history ...[/dim]")
    for message in router.context_manager.history[-6:]:
        if message['role'] == 'user':
            console.print(f"> {message['content']}")
        elif message['role'] == 'assistant':
            console.print(Markdown(message['content']))
    console.print("[dim]....................[/dim]\n")


    while True:
        try:
            user_input = console.input("You > ")
            if not user_input.strip():
                continue

            with console.status("[yellow]Thinking...[/yellow]", spinner="dots"):
                router.process_message(user_input, source="console")

        except (KeyboardInterrupt, EOFError):
            break

    console.print("\n[bold yellow]Exiting chat mode.[/bold yellow]")


@app.command()
def onboard():
    """
    Starts the conversational onboarding process to set up AI and user identity.
    """
    console.print(
        Panel(
            "Welcome to the IronClaw Onboarding process!",
            title="[bold magenta]✨ Identity Setup[/bold magenta]",
            expand=False,
        )
    )
    run_onboarding_session()
    
    console.print("\n[bold green]✅ Onboarding complete![/bold green]")
    if questionary.confirm("Would you like to configure communication channels (like Telegram) now?").ask():
        configure_channels()


@app.command(name="config")
def config_command(
    provider: bool = typer.Option(False, "--provider", help="Update the LLM provider directly.")
):
    """Launches an interactive menu to configure the agent or update the provider."""
    if provider:
        update_provider()
        return

    console.print(
        Panel("⚙️ [bold blue]Interactive Configuration[/bold blue]", expand=False)
    )

    while True:
        main_choice = questionary.select(
            "Configuration Menu",
            choices=[
                "👤 Identity",
                "🔧 Provider (Update LLM)",
                "📡 Channels",
                "🛠️ Tools",
                questionary.Separator(),
                "❌ Exit",
            ],
        ).ask()

        if not main_choice or main_choice == "❌ Exit":
            break

        if main_choice == "👤 Identity":
            console.print(
                "[bold yellow]This will start the conversational setup to redefine the AI and user profiles.[/bold yellow]"
            )
            if questionary.confirm("Do you want to proceed?").ask():
                run_onboarding_session()
            else:
                console.print("[dim]Operation cancelled.[/dim]")
        
        elif main_choice == "🔧 Provider (Update LLM)":
            update_provider()

        elif main_choice == "📡 Channels":
            configure_channels()

        elif main_choice == "🛠️ Tools":
            console.print("[yellow]Tool configuration is not yet implemented.[/yellow]")

        if main_choice != "❌ Exit":
            questionary.press_any_key_to_continue(
                "Press any key to return to the menu..."
            ).ask()


@app.command()
def update():
    """Safely updates the agent to the latest version from the main branch."""
    project_root = BASE_DIR
    console.rule("[bold blue]IronClaw Safe Update[/bold blue]")

    if not (project_root / ".git").is_dir():
        console.print("[bold red]Error: Not a Git repository. Cannot update.[/bold red]")
        raise typer.Exit(1)

    if not questionary.confirm(
        "This will reset your local code to the latest 'origin/main'. "
        "User data (like identities and memory) will be preserved. Are you sure?"
    ).ask():
        console.print("[yellow]Update cancelled.[/yellow]")
        return

    with tempfile.TemporaryDirectory(prefix="ironclaw_backup_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        console.print("📦 Backing up user data...")
        backup_paths = {
            "data": DATA_ROOT,
            ".env": ENV_PATH,
        }
        for name, path in backup_paths.items():
            if path.exists():
                dest = temp_dir / name
                if path.is_dir():
                    shutil.copytree(path, dest)
                else:
                    shutil.copy(path, dest)

        try:
            console.print("⬇️ Fetching latest version...")
            subprocess.run(
                ["git", "fetch", "--all"],
                check=True,
                cwd=project_root,
                capture_output=True,
            )
            console.print("🔄 Resetting core code to 'origin/main'...")
            subprocess.run(
                ["git", "reset", "--hard", "origin/main"],
                check=True,
                cwd=project_root,
                capture_output=True,
            )

            console.print("♻️ Restoring user data...")
            for item in temp_dir.iterdir():
                source_path = item
                target_path = project_root / item.name
                if target_path.exists():
                    if target_path.is_dir():
                        shutil.rmtree(target_path)
                    else:
                        target_path.unlink()
                if source_path.is_dir():
                    shutil.copytree(source_path, target_path)
                else:
                    shutil.copy(source_path, target_path)

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Git update failed: {e.stderr.decode()}[/bold red]")
            console.print("[yellow]Update failed. Restoring from backup...[/yellow]")
            raise typer.Exit(1)

        console.print("🐍 Installing/updating dependencies...")
        try:
            subprocess.run(
                ["pip", "install", "-r", "requirements.txt"],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            console.print(f"[bold red]Dependency installation failed: {e}[/bold red]")

    console.rule("[bold green]✅ Update Complete[/bold green]")


if __name__ == "__main__":
    app()
