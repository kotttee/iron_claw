import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import questionary
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Core components
from src.core.router import Router
from src.core.context_manager import ContextManager

# Import the setup wizard dynamically
try:
    from setup import run_setup_wizard
except ImportError:
    run_setup_wizard = None

# --- App Setup ---
app = typer.Typer(name="ironclaw", help="A modular, open-source AI Agent Platform.", add_completion=False)
console = Console()

# --- Helper for finding project root ---
def get_project_root() -> Path:
    return Path(__file__).parent.resolve()

# --- CLI Commands ---

@app.command()
def talk():
    """
    Starts the IronClaw terminal interface for seamless, continuous chat.
    History is shared with all channels (e.g., Telegram).
    """
    try:
        router = Router()
        context = router.context_manager
    except ValueError as e:
        console.print(f"[bold red]Initialization Error: {e}[/bold red]")
        console.print("[yellow]Hint: Have you run the setup wizard yet? (`python setup.py`)[/yellow]")
        raise typer.Exit(1)

    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel("IronClaw Terminal Interface | Press Ctrl+C to Exit", title="[bold green]🗣️ Live Chat[/bold green]", expand=False))

    # Display the last few messages to give context
    recent_history = context.get_recent_display(n=2)
    if recent_history:
        console.print("[dim]...continuing conversation...[/dim]")
        for msg in recent_history:
            if msg['role'] == 'user':
                console.print(f"[cyan]You:[/cyan] {msg['content']}")
            else:
                console.print(f"[green]AI:[/green]")
                console.print(Markdown(msg['content']))
        console.print("-" * 20)

    while True:
        try:
            user_input = questionary.text("You >", qmark="").ask()
            if user_input is None: # Ctrl+C was pressed
                break
            if not user_input.strip():
                continue

            with console.status("[yellow]Thinking...[/yellow]", spinner="dots"):
                response = router.process_message(user_input, source="console")
            
            console.print(f"[green]AI:[/green]")
            console.print(Markdown(response))

        except KeyboardInterrupt:
            break
    
    console.print("\n[bold yellow]Exiting chat mode.[/bold yellow]")


@app.command(name="config")
def config_command():
    """Launches an interactive TUI to configure the agent."""
    console.print(Panel("⚙️ [bold blue]Interactive Configuration[/bold blue]", expand=False))
    
    # This relies on setup.py being in the same directory or accessible.
    try:
        from setup import handle_plugin_menu, handle_identity_config
    except ImportError:
        console.print("[bold red]Error: Could not import setup functions. Ensure setup.py is accessible.[/bold red]")
        return

    while True:
        main_choice = questionary.select(
            "Configuration Menu",
            choices=[
                "📡 Manage Channels",
                "🛠️ Manage Tools",
                "🧠 Configure Core Settings",
                "👤 Configure Identity",
                questionary.Separator(),
                "❌ Exit"
            ]
        ).ask()

        if not main_choice or main_choice == "❌ Exit":
            break

        if main_choice == "📡 Manage Channels":
            handle_plugin_menu("Channels")
        elif main_choice == "🛠️ Manage Tools":
            handle_plugin_menu("Tools")
        elif main_choice == "👤 Configure Identity":
            handle_identity_config()
        elif main_choice == "🧠 Configure Core Settings":
            context = ContextManager()
            new_limit_str = questionary.text(
                "Enter new short-term memory limit (messages):",
                default=str(context.max_history_limit)
            ).ask()
            try:
                new_limit = int(new_limit_str)
                context.update_limit(new_limit)
                console.print(f"[green]✔ History limit updated to {new_limit}.[/green]")
            except (ValueError, TypeError):
                console.print("[red]Invalid input. Please enter a number.[/red]")
        
        questionary.press_any_key_to_continue("Press any key to return to the menu...").ask()

@app.command(name="update")
def update_command():
    """Safely updates the agent to the latest version from the main branch."""
    project_root = get_project_root()
    console.rule("[bold blue]IronClaw Safe Update[/bold blue]")

    if not (project_root / ".git").is_dir():
        console.print("[bold red]Error: Not a Git repository. Cannot update.[/bold red]")
        raise typer.Exit(1)

    if not questionary.confirm("This will reset your local code to the latest 'origin/main'. User data will be preserved. Are you sure?").ask():
        console.print("[yellow]Update cancelled.[/yellow]")
        return

    with tempfile.TemporaryDirectory(prefix="ironclaw_backup_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        
        console.print("📦 Backing up user data...")
        backup_paths = {
            "env": project_root / ".env",
            "data": project_root / "data",
            "custom": project_root / "src" / "custom",
        }
        
        # Use copy instead of move for safer backup
        for name, path in backup_paths.items():
            if path.exists():
                if path.is_dir():
                    shutil.copytree(path, temp_dir / name)
                else:
                    shutil.copy(path, temp_dir / name)

        try:
            console.print("⬇️ Fetching latest version...")
            subprocess.run(["git", "fetch", "--all"], check=True, cwd=project_root, capture_output=True)
            console.print("🔄 Resetting core code to 'origin/main'...")
            subprocess.run(["git", "reset", "--hard", "origin/main"], check=True, cwd=project_root, capture_output=True)
            
            console.print("♻️ Restoring user data...")
            for item in temp_dir.iterdir():
                source_path = temp_dir / item.name
                target_path = project_root / item.name
                if item.name == "custom":
                    target_path = project_root / "src" / "custom"
                
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
            console.print("[yellow]Update failed. No changes were made to your local files.[/yellow]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred during restore: {e}[/bold red]")
            console.print("[yellow]Your original data is safe in the backup location, but was not restored automatically.[/yellow]")
            raise typer.Exit(1)


        try:
            console.print("🐍 Installing/updating dependencies...")
            pip_path = shutil.which("pip")
            subprocess.run([pip_path, "install", "-r", str(project_root / "requirements.txt")], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            console.print(f"[bold red]Dependency installation failed: {e}[/bold red]")

    console.rule("[bold green]✅ Update Complete[/bold green]")

@app.command(name="setup")
def setup_command():
    """
    Shows an interactive prompt to run the setup wizard or reset user data.
    """
    project_root = get_project_root()
    console.rule("[bold magenta]IronClaw Setup & Reset[/bold magenta]")

    choices = [
        questionary.Choice("🚀 Run Configuration Wizard", value="wizard"),
        questionary.Separator(),
        questionary.Choice("🔥 Delete ALL user data (data/, .env, src/custom/)", value="all"),
        questionary.Choice("🗑️ Delete conversation history (data/memory.json)", value="history"),
        questionary.Choice("🗑️ Delete plugin configurations (data/configs/)", value="configs"),
        questionary.Choice("🗑️ Delete identity profiles (data/identity/)", value="identity"),
        questionary.Separator(),
        questionary.Choice("❌ Cancel", value="cancel")
    ]

    if not run_setup_wizard:
        choices[0] = questionary.Choice("[Unavailable] Run Configuration Wizard", disabled="setup.py not found")

    choice = questionary.select(
        "Select an option:",
        choices=choices
    ).ask()

    if not choice or choice == "cancel":
        console.print("[yellow]Operation cancelled.[/yellow]")
        raise typer.Exit()

    if choice == "wizard":
        if run_setup_wizard:
            run_setup_wizard()
        else:
            console.print("[bold red]Error: Could not import `run_setup_wizard` from setup.py.[/bold red]")
        raise typer.Exit()

    # Confirmation prompt for destructive operations
    console.print(Panel("⚠️ [bold yellow]Warning:[/bold yellow] The actions below are destructive and cannot be undone.", expand=False))
    if not questionary.confirm(f"Are you absolutely sure you want to proceed with '{choice}'?").ask():
        console.print("[yellow]Operation cancelled.[/yellow]")
        raise typer.Exit()

    # Define paths based on project root
    data_dir = project_root / "data"
    env_file = project_root / ".env"
    custom_dir = project_root / "src" / "custom"
    memory_file = data_dir / "memory.json"
    configs_dir = data_dir / "configs"
    identity_dir = data_dir / "identity"

    deleted_items = []
    
    def safe_rmtree(path: Path):
        if path.is_dir():
            shutil.rmtree(path)
            deleted_items.append(f"Directory: {path.relative_to(project_root)}")

    def safe_unlink(path: Path):
        if path.is_file():
            path.unlink()
            deleted_items.append(f"File: {path.relative_to(project_root)}")

    if choice == "all":
        console.print("[bold red]Deleting all user data...[/bold red]")
        safe_rmtree(data_dir)
        safe_unlink(env_file)
        safe_rmtree(custom_dir)
        # Recreate empty dirs
        data_dir.mkdir(exist_ok=True)
        custom_dir.mkdir(exist_ok=True)
        (custom_dir / '.gitkeep').touch()

    elif choice == "history":
        console.print("Deleting conversation history...")
        safe_unlink(memory_file)

    elif choice == "configs":
        console.print("Deleting plugin configurations...")
        safe_rmtree(configs_dir)

    elif choice == "identity":
        console.print("Deleting identity profiles...")
        safe_rmtree(identity_dir)

    if deleted_items:
        console.print("\n[bold green]Successfully deleted:[/bold green]")
        for item in deleted_items:
            console.print(f"- {item}")
    else:
        console.print("\n[yellow]No items were found to delete.[/yellow]")

    console.rule("[bold green]✅ Reset Complete[/bold green]")

if __name__ == "__main__":
    app()
