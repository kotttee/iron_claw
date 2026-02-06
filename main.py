import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.spinner import Spinner

# --- Core Imports ---
from src.core.router import MessageRouter
from src.core.scheduler import SchedulerManager
from src.core.plugin_loader import load_plugins
from src.interfaces.channel import BaseChannel

# --- App Setup ---
app = typer.Typer(name="ironclaw", help="A modular, open-source AI Agent Platform.", add_completion=False)
console = Console()

# --- Project Paths ---
try:
    PROJECT_ROOT = Path(os.environ["IRONCLAW_ROOT"])
except KeyError:
    PROJECT_ROOT = Path.home() / ".iron_claw"
    if not PROJECT_ROOT.exists():
        PROJECT_ROOT = Path(__file__).parent.resolve()

CONFIG_PATH = PROJECT_ROOT / "data/config.json"
AI_IDENTITY_PATH = PROJECT_ROOT / "data/identity/ai.md"
USER_IDENTITY_PATH = PROJECT_ROOT / "data/identity/user.md"
HISTORY_PATH = PROJECT_ROOT / "data/logs/history.jsonl"

def get_editor() -> str:
    return os.environ.get("EDITOR", "nano")

@app.command()
def start():
    """Starts the IronClaw agent and runs all enabled channels."""
    console.rule("[bold blue]IronClaw Agent Initializing[/bold blue]")

    if not CONFIG_PATH.exists():
        console.print(f"[bold red]Error: Config file not found at '{CONFIG_PATH}'.[/bold red]")
        console.print("Please run [bold cyan]ironclaw setup[/bold cyan] first.")
        raise typer.Exit(code=1)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config: Dict[str, Any] = json.load(f)
    except Exception as e:
        console.print(f"[bold red]Error reading config file: {e}[/bold red]")
        raise typer.Exit(code=1)

    scheduler = SchedulerManager()
    router = MessageRouter(config, scheduler)
    scheduler.start(router)

    all_plugin_classes = load_plugins(BaseChannel, "channels")
    all_plugins = {p().plugin_id: p for p in all_plugin_classes}

    async def run_agent():
        tasks = []
        enabled_channels = config.get("channels", {})
        if not enabled_channels:
            console.print("[bold yellow]Warning: No channels are enabled.[/bold yellow]")
            return

        for plugin_id, plugin_config in enabled_channels.items():
            if plugin_class := all_plugins.get(plugin_id):
                channel_instance = plugin_class()
                router.register_channel(channel_instance)
                tasks.append(asyncio.create_task(channel_instance.start(plugin_config, router)))
            else:
                console.print(f"[bold red]Warning: Configured plugin '{plugin_id}' not found.[/bold red]")
        
        if not tasks:
            console.print("[bold red]Error: No valid channels could be started.[/bold red]")
            return

        console.rule("[bold green]IronClaw Agent is Running[/bold green]")
        await asyncio.gather(*tasks)

    try:
        with Spinner("dots", text="Agent is running... Press Ctrl+C to stop."):
            asyncio.run(run_agent())
    except KeyboardInterrupt:
        console.print("\n")
    finally:
        console.rule("[bold magenta]Shutdown signal received.[/bold magenta]")
        scheduler.stop()
        console.print("[green]✔ Scheduler shut down gracefully.[/green]")

@app.command()
def settings():
    """Shows an interactive menu to configure the agent."""
    console.rule("[bold cyan]IronClaw Settings[/bold cyan]")
    
    while True:
        choice = Prompt.ask(
            "Choose an option",
            choices=["1", "2", "3", "4", "5", "q"],
            description=("[1] Edit AI Persona\n[2] Edit User Profile\n[3] Re-run Core Setup\n"
                         "[4] View Memory Stats\n[5] Reset/Clear Logs\n[q] Quit")
        )
        if choice == "q": break
        
        if choice == "1":
            subprocess.run([get_editor(), str(AI_IDENTITY_PATH)])
        elif choice == "2":
            subprocess.run([get_editor(), str(USER_IDENTITY_PATH)])
        elif choice == "3":
            if Confirm.ask("This will launch the core setup wizard. Continue?"):
                setup_command()
        elif choice == "4":
            if HISTORY_PATH.exists():
                lines = len(HISTORY_PATH.read_text().splitlines())
                size_kb = HISTORY_PATH.stat().st_size / 1024
                console.print(f"Interaction History: {lines} entries, {size_kb:.2f} KB")
            else:
                console.print("No interaction history found.")
        elif choice == "5":
            if Confirm.ask("[bold red]Delete all logs?[/bold red]"):
                if HISTORY_PATH.exists():
                    HISTORY_PATH.unlink()
                console.print("History log cleared.")
        console.print("-" * 20)

@app.command()
def update():
    """Updates IronClaw by pulling the latest changes and installing dependencies."""
    console.rule("[bold blue]Updating IronClaw[/bold blue]")
    try:
        subprocess.run(["git", "pull"], check=True, cwd=PROJECT_ROOT)
        pip_path = PROJECT_ROOT / "venv" / "bin" / "pip"
        subprocess.run([str(pip_path), "install", "-r", str(PROJECT_ROOT / "requirements.txt")], check=True)
        console.print("\n[bold green]✔ IronClaw updated successfully![/bold green]")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        console.print(f"\n[bold red]Update failed: {e}[/bold red]")

@app.command(name="setup")
def setup_command():
    """Runs the initial AI-driven setup wizard as a separate process."""
    console.print("[yellow]Launching the setup wizard...[/yellow]")
    try:
        # FIX: Execute setup.py as a subprocess using the same Python interpreter.
        setup_script_path = PROJECT_ROOT / "setup.py"
        subprocess.run([sys.executable, str(setup_script_path)], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        console.print(f"[bold red]The setup wizard failed to run. Error: {e}[/bold red]")

if __name__ == "__main__":
    # Set an environment variable to help scripts find the root, then change directory.
    os.environ["IRONCLAW_ROOT"] = str(PROJECT_ROOT)
    os.chdir(PROJECT_ROOT)
    app()
