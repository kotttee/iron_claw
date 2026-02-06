import json
from pathlib import Path
from typing import Any, Dict

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from src.core.paths import CONFIG_PATH, PROVIDERS_JSON_PATH


console = Console()

class SettingsManager:
    """Manages the CLI-based setup for providers."""

    def __init__(self):
        self.config = self._load_config()
        self.providers_config = self._load_providers_config()

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

    def _load_providers_config(self) -> Dict[str, Any]:
        """Loads the provider definitions from providers.json."""
        if not PROVIDERS_JSON_PATH.exists():
            console.print(f"[bold red]Error: Provider definition file not found at {PROVIDERS_JSON_PATH}[/bold red]")
            return {}
        try:
            return json.loads(PROVIDERS_JSON_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            console.print(f"[bold red]Error: Could not parse {PROVIDERS_JSON_PATH}.[/bold red]")
            return {}

    def configure_provider(self) -> bool:
        """Runs the interactive UI to configure the LLM provider."""
        console.rule("[bold blue]Provider Configuration[/bold blue]")
        if not self.providers_config:
            console.print("[bold red]Cannot configure provider. `providers.json` is missing or invalid.[/bold red]")
            return False

        provider_names = list(self.providers_config.keys())
        provider_choices = {str(i + 1): name for i, name in enumerate(provider_names)}

        console.print(Panel("Select your LLM Provider.", title="[bold cyan]LLM Setup[/bold cyan]", border_style="cyan"))
        choice_desc = "\n".join([f"[{i}] {name}" for i, name in provider_choices.items()])
        choice = Prompt.ask(f"Choose an option\n\n{choice_desc}", choices=list(provider_choices.keys()))

        provider_name = provider_choices[choice]
        provider_details = self.providers_config[provider_name]
        api_key_name = provider_details.get("api_key_name", "API_KEY")
        api_key = Prompt.ask(f"Enter your {api_key_name}")
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
