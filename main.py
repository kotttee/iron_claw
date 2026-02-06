import asyncio
import json
import os
import subprocess
import sys
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

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
# ... other paths

# --- Helper Functions for Safe Update ---

def _backup_user_data(temp_dir: Path) -> bool:
    """Moves critical user data to a temporary backup directory."""
    console.print("📦 Backing up user data...")
    backup_paths = {
        "env": PROJECT_ROOT / ".env",
        "data": PROJECT_ROOT / "data",
        "custom": PROJECT_ROOT / "src/custom",
    }
    
    has_backed_up = False
    for name, path in backup_paths.items():
        if path.exists():
            try:
                shutil.move(str(path), str(temp_dir / name))
                has_backed_up = True
            except Exception as e:
                console.print(f"[bold red]Error backing up {path.name}: {e}[/bold red]")
                return False
    
    if not has_backed_up:
        console.print("[yellow]No user data found to back up.[/yellow]")

    return True

def _restore_user_data(temp_dir: Path):
    """Restores user data from the backup directory, overwriting placeholders."""
    console.print("♻️ Restoring user data...")
    for item in temp_dir.iterdir():
        target_path = PROJECT_ROOT / item.name
        if item.name == "custom":
            target_path = PROJECT_ROOT / "src/custom"

        # If a placeholder directory was created by the update, remove it first.
        if target_path.is_dir():
            shutil.rmtree(target_path, ignore_errors=True)
        elif target_path.is_file():
            target_path.unlink()
            
        try:
            shutil.move(str(item), str(target_path))
        except Exception as e:
            console.print(f"[bold red]Error restoring {item.name}: {e}[/bold red]")

# --- CLI Commands ---

@app.command()
def start():
    """Initializes the Kernel and starts the IronClaw agent."""
    try:
        kernel = Kernel(config_path=CONFIG_PATH)
        kernel.run()
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[bold red]Could not start agent: {e}[/bold red]")
        raise typer.Exit(code=1)

@app.command(name="update")
def update_command():
    """Safely updates the agent to the latest version using a backup-reset-restore strategy."""
    console.rule("[bold blue]IronClaw Safe Update[/bold blue]")
    
    if not (PROJECT_ROOT / ".git").is_dir():
        console.print("[bold red]Error: Not a Git repository. Cannot update.[/bold red]")
        raise typer.Exit(code=1)

    with tempfile.TemporaryDirectory(prefix="ironclaw_backup_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        # 1. Backup
        if not _backup_user_data(temp_dir):
            console.print("[bold red]Update aborted due to backup failure.[/bold red]")
            raise typer.Exit(code=1)

        # 2. Hard Reset
        try:
            console.print("⬇️ Fetching latest version from the remote repository...")
            subprocess.run(["git", "fetch", "--all"], check=True, cwd=PROJECT_ROOT, capture_output=True)
            
            console.print("🔄 Resetting core code to 'origin/main'...")
            subprocess.run(["git", "reset", "--hard", "origin/main"], check=True, cwd=PROJECT_ROOT, capture_output=True)
            console.print("[green]✔ Core code updated successfully.[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Git update failed: {e.stderr.decode()}[/bold red]")
            _restore_user_data(temp_dir) # Attempt to restore on failure
            raise typer.Exit(code=1)

        # 3. Restore
        _restore_user_data(temp_dir)

        # 4. Re-install Dependencies
        try:
            console.print("🐍 Installing/updating dependencies...")
            pip_path = PROJECT_ROOT / "venv" / "bin" / "pip"
            subprocess.run([str(pip_path), "install", "-r", str(PROJECT_ROOT / "requirements.txt")], check=True, capture_output=True)
            console.print("[green]✔ Dependencies are up to date.[/green]")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            console.print(f"[bold red]Dependency installation failed: {e}[/bold red]")
            console.print("Please try running 'pip install -r requirements.txt' manually.")

    console.rule("[bold green]✅ Update Complete[/bold green]")
    console.print("Restarting the agent is recommended to apply all changes.")

@app.command(name="setup")
def setup_command():
    """Runs the initial AI-driven setup wizard directly."""
    # Update the path to the providers.json file
    from src.core import setup_wizard
    setup_wizard.PROVIDERS_PATH = PROJECT_ROOT / "providers.json"
    console.print("[yellow]Launching the setup wizard...[/yellow]")
    run_ai_wizard()

# ... (other commands like 'settings' can be added here)

if __name__ == "__main__":
    os.environ["IRONCLAW_ROOT"] = str(PROJECT_ROOT)
    os.chdir(PROJECT_ROOT)
    app()
