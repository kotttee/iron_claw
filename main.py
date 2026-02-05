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

# --- Core Imports (assuming they exist from previous steps) ---
from src.core.router import MessageRouter
from src.core.scheduler import SchedulerManager
from src.core.plugin_loader import load_plugins
from src.interfaces.channel import BaseChannel

# --- App Setup ---
app = typer.Typer(name="ironclaw", help="A modular, open-source AI Agent Platform.")
console = Console()

# --- Project Paths ---
# Ensure the script can find its root directory to locate data files
try:
    # This works when run via the runner script which sets the CWD
    PROJECT_ROOT = Path.cwd()
except FileNotFoundError:
    # Fallback for environments where CWD might not exist
    PROJECT_ROOT = Path(__file__).parent.resolve()

CONFIG_PATH = PROJECT_ROOT / "data/config.json"
AI_IDENTITY_PATH = PROJECT_ROOT / "data/identity/ai.md"
USER_IDENTITY_PATH = PROJECT_ROOT / "data/identity/user.md"
HISTORY_PATH = PROJECT_ROOT / "data/logs/history.jsonl"

def get_editor() -> str:
    """Returns the user's default editor, falling back to nano."""
    return os.environ.get("EDITOR", "nano")

@app.command()
def start():
    """Starts the IronClaw agent and runs all enabled channels."""
    console.rule("[bold blue]IronClaw Agent Initializing[/bold blue]")

    if not CONFIG_PATH.exists():
        console.print(f"[bold red]Error: Config file not found at '{CONFIG_PATH}'.[/bold red]")
        console.print("Please run [bold cyan]ironclaw setup[/bold cyan] or [bold cyan]ironclaw settings[/bold cyan] first.")
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
            console.print("[bold yellow]Warning: No channels are enabled in the configuration.[/bold yellow]")
            return

        for plugin_id, plugin_config in enabled_channels.items():
            if plugin_class := all_plugins.get(plugin_id):
                tasks.append(asyncio.create_task(plugin_class().start(plugin_config, router)))
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
            description=(
                "[1] Edit AI Persona\n"
                "[2] Edit User Profile\n"
                "[3] Edit API Keys\n"
                "[4.0] View Memory Stats\n"
                "[5] Reset/Clear Logs\n"
                "[q] Quit"
            )
        )

        if choice == "1":
            subprocess.run([get_editor(), str(AI_IDENTITY_PATH)])
        elif choice == "2":
            subprocess.run([get_editor(), str(USER_IDENTITY_PATH)])
        elif choice == "3":
            if not CONFIG_PATH.exists():
                console.print("[yellow]Config file not found. Creating a new one.[/yellow]")
                config = {}
            else:
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
            
            api_key = Prompt.ask("Enter new LLM API Key (leave blank to keep current)")
            if api_key:
                if "llm" not in config: config["llm"] = {}
                config["llm"]["api_key"] = api_key
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(config, f, indent=4)
                console.print("[green]API Key updated.[/green]")
        elif choice == "4":
            if HISTORY_PATH.exists():
                lines = len(HISTORY_PATH.read_text().splitlines())
                size_kb = HISTORY_PATH.stat().st_size / 1024
                console.print(f"Interaction History: {lines} entries, {size_kb:.2f} KB")
            else:
                console.print("No interaction history found.")
        elif choice == "5":
            if Confirm.ask("[bold red]Are you sure you want to delete all logs?[/bold red]"):
                if HISTORY_PATH.exists():
                    HISTORY_PATH.unlink()
                    console.print("History log cleared.")
        elif choice == "q":
            break
        console.print("-" * 20)

@app.command()
def update():
    """Updates IronClaw by pulling the latest changes and installing dependencies."""
    console.rule("[bold blue]Updating IronClaw[/bold blue]")
    
    try:
        console.print("Pulling latest changes from git...")
        subprocess.run(["git", "pull"], check=True, cwd=PROJECT_ROOT)
        
        console.print("Installing/updating dependencies...")
        pip_path = PROJECT_ROOT / "venv" / "bin" / "pip"
        subprocess.run([str(pip_path), "install", "-r", str(PROJECT_ROOT / "requirements.txt")], check=True)
        
        console.print("\n[bold green]✔ IronClaw updated successfully![/bold green]")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        console.print(f"\n[bold red]Update failed: {e}[/bold red]")
        console.print("Please ensure you are in the project directory and git is installed.")

# You can add the setup command from the previous step here as well
@app.command(name="setup")
def setup_command():
    """Runs the initial AI-driven setup wizard."""
    from setup import run_ai_wizard
    run_ai_wizard()

if __name__ == "__main__":
    # Change CWD to the project root so file paths work correctly
    os.chdir(PROJECT_ROOT)
    app()
