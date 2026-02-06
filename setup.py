import questionary
from rich.console import Console
from rich.panel import Panel
from dotenv import set_key, get_key

# Refactored to use the centralized pathing system
from src.core.paths import ENV_PATH, IDENTITY_DIR, ensure_dirs
from src.core.plugin_manager import get_all_plugins
from src.core.providers import provider_factory

# --- Constants ---
console = Console()

# --- TUI Handlers ---

def handle_plugin_menu(category: str):
    """Manages the TUI for a specific plugin category (channels or tools)."""
    plugins = get_all_plugins()
    plugin_list = plugins.get(category.lower(), [])
    
    if not plugin_list:
        console.print(f"[yellow]No {category} found.[/yellow]")
        return

    while True:
        choices = [
            questionary.Choice(
                title=f"{p.get_status_emoji()} {p.name.capitalize()}",
                value=p
            ) for p in plugin_list
        ]
        choices.append(questionary.Separator())
        choices.append(questionary.Choice(title="⬅️ Back", value="back"))

        selected_plugin = questionary.select(
            f"Manage {category}",
            choices=choices,
            use_indicator=True
        ).ask()

        if not selected_plugin or selected_plugin == "back":
            break

        # --- Plugin Action Menu ---
        while True:
            action = questionary.select(
                f"Actions for {selected_plugin.name.capitalize()}",
                choices=[
                    questionary.Choice(
                        f"Toggle Status (Currently: {selected_plugin.get_status_emoji()})",
                        value="toggle"
                    ),
                    questionary.Choice("⚙️ Configure Settings", value="configure"),
                    questionary.Separator(),
                    questionary.Choice("⬅️ Back", value="back")
                ]
            ).ask()

            if not action or action == "back":
                break
            
            if action == "toggle":
                new_state = selected_plugin.toggle_enabled()
                console.print(f"[green]✔ {selected_plugin.name.capitalize()} is now {'enabled' if new_state else 'disabled'}.[/green]")
            elif action == "configure":
                selected_plugin.setup_wizard()
                console.print(f"[green]✔ Re-ran configuration for {selected_plugin.name.capitalize()}.[/green]")


def handle_ai_core_config():
    """Interactive setup for the core LLM provider using the ProviderFactory."""
    console.print(Panel("🧠 Configure AI Core", style="bold blue", expand=False))
    
    ensure_dirs()
    if not ENV_PATH.exists():
        ENV_PATH.touch()

    provider_names = provider_factory.get_provider_names()
    if not provider_names:
        console.print("[bold red]Error: Could not load any providers from providers.json.[/bold red]")
        return

    provider_display_name = questionary.select(
        "Select LLM Provider:",
        choices=provider_names,
        default=get_key(str(ENV_PATH), "LLM_PROVIDER_NAME") or provider_names[0]
    ).ask()

    if not provider_display_name:
        return

    provider_config = provider_factory.get_provider_config(provider_display_name)
    if not provider_config:
        console.print(f"[bold red]Could not find config for {provider_display_name}[/bold red]")
        return
        
    api_key_name = provider_config.get("api_key_name", "API_KEY")

    api_key = questionary.text(
        f"Enter your {api_key_name}:",
        default=get_key(str(ENV_PATH), api_key_name) or ""
    ).ask()

    if not api_key:
        console.print("[red]API Key is required.[/red]")
        return

    try:
        provider = provider_factory.create_provider(provider_display_name, api_key)
        
        with console.status("[yellow]Testing connection and fetching models...[/yellow]"):
            models = provider.list_models()
        
        if not models:
            console.print("[yellow]Could not fetch models automatically. Please enter manually.[/yellow]")
            model_name = questionary.text("Model name:").ask()
        else:
            console.print("[green]✔ Models fetched successfully.[/green]")
            model_name = questionary.select("Select a model:", choices=models).ask()

        if not model_name:
            return

        set_key(str(ENV_PATH), "LLM_PROVIDER_NAME", provider_display_name)
        set_key(str(ENV_PATH), api_key_name, api_key)
        set_key(str(ENV_PATH), "LLM_MODEL", model_name)
        
        console.print("[bold green]✔ AI Core configured successfully![/bold green]")

    except Exception as e:
        console.print(f"[bold red]An error occurred: {e}[/bold red]")


def handle_identity_config():
    """Interactive setup for the agent's identity."""
    console.print(Panel("👤 Configure Identity", style="bold magenta", expand=False))
    
    ensure_dirs()
    ai_md_path = IDENTITY_DIR / "ai.md"
    user_md_path = IDENTITY_DIR / "user.md"
    
    ai_name = questionary.text("What is my name?", default="IronClaw").ask()
    ai_role = questionary.text("Describe my core personality/role:", default="A helpful AI assistant.").ask()
    user_info = questionary.text("Describe the user (you):", default="A developer building AI applications.").ask()

    ai_md_content = f"# Name\n{ai_name}\n\n# Role\n{ai_role}"
    ai_md_path.write_text(ai_md_content)
    user_md_path.write_text(user_info)

    console.print("[bold green]✔ Identity configured successfully![/bold green]")


def run_setup_wizard():
    """The main TUI loop for the setup wizard."""
    console.print(Panel("Welcome to the [bold]IronClaw[/bold] Setup Wizard", style="bold green"))
    
    while True:
        choice = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("🧠 Configure AI Core (LLM)", value="core"),
                questionary.Choice("👤 Configure Identity (Persona)", value="identity"),
                questionary.Choice("📡 Manage Channels", value="channels"),
                questionary.Choice("🛠️ Manage Tools", value="tools"),
                questionary.Separator(),
                questionary.Choice("❌ Exit", value="exit")
            ],
            use_indicator=True
        ).ask()

        if not choice or choice == "exit":
            break
        
        if choice == "core":
            handle_ai_core_config()
        elif choice == "identity":
            handle_identity_config()
        elif choice == "channels":
            handle_plugin_menu("Channels")
        elif choice == "tools":
            handle_plugin_menu("Tools")
            
        questionary.press_any_key_to_continue().ask()

if __name__ == "__main__":
    try:
        run_setup_wizard()
    except (KeyboardInterrupt, TypeError):
        console.print("\n[bold red]Setup aborted.[/bold red]")
