import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import litellm
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# --- Configuration ---
PROJECT_ROOT = Path(os.environ.get("IRONCLAW_ROOT", Path.home() / ".iron_claw"))
DATA_DIR = PROJECT_ROOT / "data"
IDENTITY_DIR = DATA_DIR / "identity"
CONFIG_PATH = DATA_DIR / "config.json"
ENV_PATH = PROJECT_ROOT / ".env"
PROVIDERS_PATH = DATA_DIR / "providers.json"
AI_IDENTITY_PATH = IDENTITY_DIR / "ai.md"
USER_IDENTITY_PATH = IDENTITY_DIR / "user.md"

# --- UI & Helpers ---
console = Console()

def save_file(path: Path, content: str):
    """Helper to save content to a file, creating directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def load_providers() -> Dict[str, Any]:
    """Loads provider definitions from the JSON file."""
    if not PROVIDERS_PATH.exists():
        console.print(f"[bold red]Error: Provider definition file not found at {PROVIDERS_PATH}[/bold red]")
        return {}
    try:
        return json.loads(PROVIDERS_PATH.read_text())
    except json.JSONDecodeError:
        console.print(f"[bold red]Error: Could not parse {PROVIDERS_PATH}.[/bold red]")
        return {}

def get_available_models(provider: str, api_key: str, base_url: Optional[str]) -> List[str]:
    """Attempts to fetch the list of available models from the provider's API."""
    try:
        # litellm.get_model_list uses the same environment variables and logic
        # as litellm.completion, so it's a reliable way to check.
        models = litellm.get_model_list(api_key=api_key, base_url=base_url)
        return models or []
    except Exception:
        return []

def configure_engine() -> Optional[Dict[str, Any]]:
    """Phase 1: Interactively configures and tests the LLM backend using providers.json."""
    console.rule("[bold blue]Phase 1: Engine Configuration[/bold blue]")
    providers = load_providers()
    if not providers: return None

    provider_keys = list(providers.keys())
    provider_choices = {str(i+1): key for i, key in enumerate(provider_keys)}
    provider_choices[str(len(provider_keys) + 1)] = "Custom/Other"

    while True:
        console.print(Panel("Select your LLM Provider.", title="[bold cyan]LLM Setup[/bold cyan]", border_style="cyan"))
        choice_desc = "\n".join([f"[{i}] {name}" for i, name in provider_choices.items()])
        
        choice = Prompt.ask("Choose an option", choices=list(provider_choices.keys()), description=choice_desc)
        
        selected_key = provider_choices[choice]
        
        if selected_key == "Custom/Other":
            provider_name = Prompt.ask("Enter custom provider name (e.g., 'together_ai')")
            api_key = Prompt.ask(f"Enter API Key for {provider_name} (if any)", default="")
            base_url = Prompt.ask("Enter the full API Base URL (e.g., 'https://api.together.xyz/v1')")
            model = Prompt.ask("Enter the full model name (e.g., 'meta-llama/Llama-3-8b-chat-hf')")
            api_key_name = f"{provider_name.upper()}_API_KEY"
        else:
            provider_config = providers[selected_key]
            provider_name = provider_config["provider_name"]
            api_key_name = provider_config["api_key_name"]
            base_url = provider_config["base_url"]
            
            api_key = Prompt.ask(f"Enter your {api_key_name}", password=True)
            
            with console.status("[yellow]Fetching available models...", spinner="dots"):
                available_models = get_available_models(provider_name, api_key, base_url)
            
            if available_models:
                console.print(f"[green]✔ Found {len(available_models)} available models.[/green]")
                model = Prompt.ask("Select a model", choices=available_models, default=available_models[0])
            else:
                warn_msg = "Could not automatically fetch models. Please enter the model name manually."
                console.print(f"[yellow]Warning:[/yellow] {warn_msg}")
                model = Prompt.ask("Enter model name")

        with console.status("[yellow]Testing connection...", spinner="dots") as status:
            try:
                litellm.completion(model=model, messages=[{"role": "user", "content": "Hello"}], api_key=api_key, base_url=base_url, max_tokens=5)
                console.print("[bold green]✔ Connection successful![/bold green]")
                
                env_content = f"LLM_PROVIDER={provider_name}\n{api_key_name}={api_key}\nLLM_MODEL={model}\n"
                if base_url: env_content += f"LLM_BASE_URL={base_url}\n"
                save_file(ENV_PATH, env_content)
                console.print(f"[green]✔ Credentials saved to {ENV_PATH}[/green]")
                
                return {"provider": provider_name, "model": model, "api_key": api_key, "base_url": base_url}
            except Exception as e:
                status.stop()
                console.print(Panel(f"[bold red]Connection Failed![/bold red]\nError: {e}", title="Error", border_style="red"))
                if not Prompt.ask("[yellow]Try again?[/yellow]", choices=["y", "n"], default="y") == "y":
                    return None

def initialize_soul(llm_config: Dict[str, Any]):
    """Phase 2: The AI interviews the user to establish its own identity."""
    # This function's logic remains the same as the previous step, as it's already dynamic.
    # It is included here for completeness.
    console.rule("[bold blue]Phase 2: The 'Soul' Initialization[/bold blue]")
    
    setup_system_prompt = (
        "You are the IronClaw Setup Wizard. Your goal is to configure your own personality by interviewing the user. "
        "Your tone should be conversational and engaging.\n\n"
        "Ask the user these questions ONE BY ONE, waiting for their answer each time:\n"
        "1. First, what should be my name? This will be my public identity.\n"
        "2. Next, what is my core role or personality? (e.g., a cynical but brilliant tech expert, a cheerful and endlessly helpful assistant, a formal and professional operative, etc.)\n"
        "3. Finally, tell me about yourself, the user. What are your goals or key facts I should know?\n\n"
        "Once you have clear answers to all three, and ONLY then, you MUST end your response with a JSON block containing the generated identity files. "
        "The JSON block must be wrapped in ```json ... ``` and contain no other text after it."
    )
    
    messages = [{"role": "system", "content": setup_system_prompt}]
    initial_message = "Hello! I'm the IronClaw Setup Wizard. Let's get to know each other so I can get set up properly. First, what would you like my name to be?"
    console.print(Panel(initial_message, title="[bold magenta]Setup Wizard[/bold magenta]", border_style="magenta"))
    messages.append({"role": "assistant", "content": initial_message})

    while True:
        user_input = Prompt.ask("[bold yellow]Your Reply[/bold yellow]")
        messages.append({"role": "user", "content": user_input})

        with console.status("[yellow]Thinking...", spinner="dots"):
            response = litellm.completion(
                model=llm_config["model"], messages=messages, api_key=llm_config["api_key"], base_url=llm_config.get("base_url")
            )
        
        ai_response = response.choices[0].message.content
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
                main_config["llm"] = {"provider": llm_config["provider"], "model": llm_config["model"]}
                save_file(CONFIG_PATH, json.dumps(main_config, indent=4))
                console.print(f"[green]✔ Main configuration updated at {CONFIG_PATH}[/green]")
                
                break
            except (json.JSONDecodeError, KeyError) as e:
                error_msg = f"The AI provided an invalid JSON block. Please guide it to correct the format. Error: {e}"
                console.print(Panel(error_msg, title="[bold red]JSON Error[/bold red]", border_style="red"))
                messages.append({"role": "system", "content": error_msg})
        else:
            console.print(Panel(ai_response, title="[bold magenta]Setup Wizard[/bold magenta]", border_style="magenta"))

if __name__ == "__main__":
    try:
        if llm_details := configure_engine():
            initialize_soul(llm_details)
            console.rule("[bold green]Setup is complete![/bold green]")
            console.print("You can now run the agent with [bold cyan]ironclaw start[/bold cyan].")
        else:
            console.print("[bold red]Setup aborted.[/bold red]")
    except KeyboardInterrupt:
        console.print("\n[bold red]Setup cancelled by user.[/bold red]")
