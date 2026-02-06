import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# Import the new native provider factory
from src.core.providers import get_provider, PROVIDER_REGISTRY

# --- Configuration ---
PROJECT_ROOT = Path(os.environ.get("IRONCLAW_ROOT", Path.home() / ".iron_claw"))
DATA_DIR = PROJECT_ROOT / "data"
IDENTITY_DIR = DATA_DIR / "identity"
CONFIG_PATH = DATA_DIR / "config.json"
ENV_PATH = PROJECT_ROOT / ".env"
AI_IDENTITY_PATH = IDENTITY_DIR / "ai.md"
USER_IDENTITY_PATH = IDENTITY_DIR / "user.md"

# --- UI & Helpers ---
console = Console()

def save_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def configure_engine() -> Optional[Dict[str, Any]]:
    """Phase 1: Configures and tests the LLM backend using the native provider system."""
    console.rule("[bold blue]Phase 1: Engine Configuration[/bold blue]")
    
    provider_names = list(PROVIDER_REGISTRY.keys())
    provider_choices = {str(i+1): name for i, name in enumerate(provider_names)}
    
    while True:
        console.print(Panel("Select your LLM Provider.", title="[bold cyan]LLM Setup[/bold cyan]", border_style="cyan"))
        choice_desc = "\n".join([f"[{i}] {name.capitalize()}" for i, name in provider_choices.items()])
        prompt_text = f"Choose an option\n\n{choice_desc}"
        choice = Prompt.ask(prompt_text, choices=list(provider_choices.keys()))
        
        provider_name = provider_choices[choice]
        api_key_name = f"{provider_name.upper()}_API_KEY"
        
        console.print(f"[yellow]Warning:[/yellow] Your API key will be visible as you type.")
        api_key = Prompt.ask(f"Enter your {api_key_name}")

        try:
            provider_instance = get_provider(provider_name, api_key)
        except ValueError as e:
            console.print(f"[bold red]Error: {e}[/bold red]")
            continue

        with console.status("[yellow]Fetching available models...", spinner="dots"):
            available_models = provider_instance.list_models()
        
        if available_models:
            console.print(f"[green]✔ Found {len(available_models)} models.[/green]")
            model = Prompt.ask("Select a model", choices=available_models, default=available_models[0])
        else:
            console.print("[yellow]Warning:[/yellow] Could not fetch models. Please enter model name manually.")
            model = Prompt.ask("Enter model name")

        with console.status("[yellow]Testing connection...", spinner="dots"):
            try:
                # Use the provider's chat method for the connection test
                provider_instance.chat(model, [{"role": "user", "content": "Hello"}], "You are a test bot.")
                console.print("[bold green]✔ Connection successful![/bold green]")
                
                env_content = f"LLM_PROVIDER={provider_name}\n{api_key_name}={api_key}\nLLM_MODEL={model}\n"
                save_file(ENV_PATH, env_content)
                console.print(f"[green]✔ Credentials saved to {ENV_PATH}[/green]")
                
                return {"provider": provider_instance, "model": model}
            except Exception as e:
                console.print(Panel(f"[bold red]Connection Failed![/bold red]\nError: {e}", title="Error", border_style="red"))
                if not Prompt.ask("[yellow]Try again?[/yellow]", choices=["y", "n"], default="y") == "y":
                    return None

def initialize_soul(engine_config: Dict[str, Any]):
    """Phase 2: The AI interviews the user to establish its own identity."""
    console.rule("[bold blue]Phase 2: The 'Soul' Initialization[/bold blue]")
    
    provider: BaseProvider = engine_config["provider"]
    model: str = engine_config["model"]
    
    system_prompt = (
        "You are the IronClaw Setup Wizard. Your goal is to configure your own personality by interviewing the user. "
        "Ask these questions ONE BY ONE, waiting for their answer each time:\n"
        "1. What should be my name?\n"
        "2. What is my core role or personality?\n"
        "3. Tell me about yourself, the user.\n\n"
        "Once you have clear answers, you MUST end your response with ONLY a JSON block wrapped in ```json ... ``` containing: "
        "{ \"ai_md\": \"...\", \"user_md\": \"...\", \"bot_name\": \"...\" }"
    )
    
    messages = []
    initial_message = "Hello! I'm the IronClaw Setup Wizard. Let's define my identity. First, what would you like my name to be?"
    console.print(Panel(initial_message, title="[bold magenta]Setup Wizard[/bold magenta]", border_style="magenta"))
    messages.append({"role": "assistant", "content": initial_message})

    while True:
        user_input = Prompt.ask("[bold yellow]Your Reply[/bold yellow]")
        messages.append({"role": "user", "content": user_input})

        with console.status("[yellow]Thinking...", spinner="dots"):
            ai_response = provider.chat(model, messages, system_prompt)
        
        messages.append({"role": "assistant", "content": ai_response})

        json_match = re.search(r"```json\s*(\{.*?\})\s*```", ai_response, re.DOTALL)
        if json_match:
            try:
                config_data = json.loads(json_match.group(1))
                console.print(Panel("Configuration data received. Finalizing setup...", title="[bold green]Complete[/bold green]", border_style="green"))
                
                save_file(AI_IDENTITY_PATH, config_data["ai_md"])
                console.print(f"[green]✔ AI identity saved to {AI_IDENTITY_PATH}[/green]")
                
                save_file(USER_IDENTITY_PATH, config_data["user_md"])
                console.print(f"[green]✔ User profile saved to {USER_IDENTITY_PATH}[/green]")
                
                main_config = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
                main_config["agent_name"] = config_data["bot_name"]
                main_config["llm"] = {"provider": provider.provider_name, "model": model} # Store provider name, not instance
                save_file(CONFIG_PATH, json.dumps(main_config, indent=4))
                console.print(f"[green]✔ Main configuration updated at {CONFIG_PATH}[/green]")
                
                break
            except (json.JSONDecodeError, KeyError) as e:
                error_msg = f"The AI provided an invalid JSON block. Error: {e}"
                console.print(Panel(error_msg, title="[bold red]JSON Error[/bold red]", border_style="red"))
                messages.append({"role": "system", "content": error_msg})
        else:
            console.print(Panel(ai_response, title="[bold magenta]Setup Wizard[/bold magenta]", border_style="magenta"))

def run_ai_wizard():
    """Main entry point function for the setup wizard."""
    try:
        if engine_details := configure_engine():
            initialize_soul(engine_details)
            console.rule("[bold green]Setup is complete![/bold green]")
        else:
            console.print("[bold red]Setup aborted.[/bold red]")
    except KeyboardInterrupt:
        console.print("\n[bold red]Setup cancelled by user.[/bold red]")

if __name__ == "__main__":
    run_ai_wizard()
