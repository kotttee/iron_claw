import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.spinner import Spinner

# --- Core Imports ---
from src.core.kernel import Kernel
from src.core.setup_wizard import run_ai_wizard

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
    """Initializes the Kernel and starts the IronClaw agent."""
    try:
        kernel = Kernel(config_path=CONFIG_PATH)
        kernel.run()
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[bold red]Could not start agent: {e}[/bold red]")
        raise typer.Exit(code=1)

@app.command()
def settings():
    """Shows an interactive menu to configure the agent."""
    console.rule("[bold cyan]IronClaw Settings[/bold cyan]")
    
    while True:
        # FIX: Combine prompt and description into a single multi-line string.
        prompt_text = (
            "Choose an option\n\n"
            "[1] Edit AI Persona\n"
            "[2] Edit User Profile\n"
            "[3] Re-run Core Setup\n"
            "[4] View Memory Stats\n"
            "[5] Reset/Clear Logs\n"
            "[q] Quit"
        )
        choice = Prompt.ask(prompt_text, choices=["1", "2", "3", "4", "5", "q"])
        
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
    """Runs the initial AI-driven setup wizard directly."""
    console.print("[yellow]Launching the setup wizard...[/yellow]")
    run_ai_wizard()

if __name__ == "__main__":
    os.environ["IRONCLAW_ROOT"] = str(PROJECT_ROOT)
    os.chdir(PROJECT_ROOT)
    app()
