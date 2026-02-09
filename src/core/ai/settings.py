import json
from pathlib import Path
from typing import Any, Dict, Optional
import questionary

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from src.core.paths import CONFIG_PATH
from src.core.providers import provider_factory


console = Console()

class SettingsManager:
    """Manages the CLI-based setup for providers."""

    def __init__(self, router: Optional[Any] = None):
        self.config = self._load_config()
        self.provider_factory = provider_factory
        self.router = router

    def _load_config(self) -> Dict[str, Any]:
        """Loads the main config.json file."""
        if not CONFIG_PATH.exists():
            return {}
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            console.print(f"[bold red]Warning: Could not read or parse existing config at {CONFIG_PATH}. Starting fresh.[/bold red]")
            return {}

    def _save_config(self):
        """Saves the current configuration to config.json."""
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(self.config, indent=4), encoding="utf-8")
        
        # If router is present, trigger re-initialization
        if self.router:
            try:
                self.router.reinitialize_provider()
                console.print("[bold green]Router: Provider re-initialized successfully.[/bold green]")
            except Exception as e:
                console.print(f"[bold red]Router: Failed to re-initialize provider: {e}[/bold red]")

    def run_main_menu(self):
        """Main interactive configuration hub."""
        while True:
            choice = questionary.select(
                "IronClaw Configuration Menu",
                choices=[
                    "🧠 Core LLM Settings",
                    "📡 Manage Channels",
                    "🛠️ Manage Plugins & Schedulers",
                    questionary.Separator(),
                    "⬅️ Back to CLI"
                ]
            ).ask()

            if not choice or "Back" in choice:
                break

            if "Core" in choice:
                self.configure_provider()
            elif "Channels" in choice:
                self._manage_components("channels")
            elif "Plugins" in choice:
                self._manage_components("tools", "schedulers")

    def _manage_components(self, *categories):
        if not self.router:
            console.print("[red]Error: Router not initialized. Cannot manage components.[/red]")
            return

        components = []
        for cat in categories:
            components.extend(self.router.plugin_manager.get(cat, []))

        if not components:
            console.print("[yellow]No components found in these categories.[/yellow]")
            return

        while True:
            comp_choices = []
            for c in components:
                prefix = "🛠️" if c.component_type == "plugin" else "📡" if c.component_type == "channel" else "⏰"
                status = "[ON]" if c.config.enabled else "[OFF]"
                comp_choices.append(questionary.Choice(
                    title=f"{status} {prefix} {c.name}",
                    value=c
                ))
            comp_choices.append("⬅️ Back")

            selected = questionary.select("Select component to configure:", choices=comp_choices).ask()
            if not selected or "Back" in selected: break
            
            # Find the actual component object
            comp_name = selected.split(" ", 1)[1]
            comp = next(c for c in components if c.name == comp_name)
            
            action = questionary.select(f"Action for {comp.name}:", choices=["Toggle Enabled", "Run Setup Wizard", "Back"]).ask()
            if action == "Toggle Enabled":
                comp.update_config({"enabled": not comp.config.enabled})
            elif action == "Run Setup Wizard":
                comp.run_setup_wizard()

    def configure_provider(self) -> bool:
        """Runs the interactive UI to configure the LLM provider."""
        console.rule("[bold blue]Provider Configuration[/bold blue]")
        provider_names = self.provider_factory.get_provider_names()
        if not provider_names:
            console.print("[bold red]Cannot configure provider. `providers.json` is missing or invalid.[/bold red]")
            return False

        provider_choices = {str(i + 1): name for i, name in enumerate(provider_names)}

        console.print(Panel("Select your LLM Provider.", title="[bold cyan]LLM Setup[/bold cyan]", border_style="cyan"))
        choice_desc = "\n".join([f"[{i}] {name}" for i, name in provider_choices.items()])
        choice = Prompt.ask(f"Choose an option\n\n{choice_desc}", choices=list(provider_choices.keys()))

        provider_name = provider_choices[choice]
        provider_details = self.provider_factory.get_provider_config(provider_name)
        api_key_name = provider_details.get("api_key_name", "API_KEY")
        api_key = Prompt.ask(f"Enter your {api_key_name}")

        try:
            provider = self.provider_factory.create_provider(provider_name, api_key)
            models = provider.list_models()
        except Exception as e:
            console.print(f"[bold red]Error fetching models: {e}[/bold red]")
            models = []

        model = None
        if models:
            model_choices = {str(i + 1): m for i, m in enumerate(models)}
            model_choices[str(len(models) + 1)] = "Enter manually"
            
            console.print("\nSelect a model:")
            model_choice_desc = "\n".join([f"[{i}] {m}" for i, m in model_choices.items()])
            model_choice = Prompt.ask(model_choice_desc, choices=list(model_choices.keys()))

            if model_choices[model_choice] == "Enter manually":
                model = Prompt.ask("Enter the model name")
            else:
                model = model_choices[model_choice]
        else:
            console.print("\nCould not fetch models, or no models available.")
            model = Prompt.ask("Enter the model name you want to use (e.g., gpt-4-turbo)")

        self.config["llm"] = {
            "provider_name": provider_name,
            "api_key": api_key,
            "model": model,
        }
        
        if "base_url" in provider_details:
            self.config["llm"]["base_url"] = provider_details["base_url"]

        self._save_config()
        console.print(f"[green]✔ Provider '{provider_name}' and model '{model}' configured.[/green]")
        return True

    def run_full_setup(self):
        """Runs the complete setup wizard for provider."""
        console.print(Panel("Welcome to the IronClaw Setup Wizard!", title="[bold green]Setup[/bold green]"))
        if self.configure_provider():
            console.rule("[bold green]Setup Complete[/bold green]")
            console.print(f"Configuration saved to {CONFIG_PATH}")
        else:
            console.print("[bold red]Setup failed.[/bold red]")

    def is_provider_configured(self) -> bool:
        """Checks if the LLM provider is configured in config.json."""
        return "llm" in self.config and "provider_name" in self.config["llm"] and "api_key" in self.config["llm"]
