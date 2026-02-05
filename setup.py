import json
import os
from pathlib import Path

from litellm import completion
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# --- Configuration ---
IDENTITY_DIR = Path("data/identity")
CONFIG_PATH = Path("data/config.json")
AI_IDENTITY_PATH = IDENTITY_DIR / "ai.md"
USER_IDENTITY_PATH = IDENTITY_DIR / "user.md"

def save_file(path: Path, content: str):
    """Helper to save content to a file, creating directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def run_ai_wizard():
    """
    An interactive, AI-driven wizard to set up the agent's identity.
    """
    console = Console()
    console.rule("[bold magenta]IronClaw AI Setup Wizard[/bold magenta]")

    # --- API Key Setup ---
    console.print(Panel("First, I need an API key for an LLM provider like OpenAI or Groq.", title="[bold cyan]API Key[/bold cyan]", border_style="cyan"))
    api_key = Prompt.ask("Enter your LLM API Key", password=True)
    os.environ["OPENAI_API_KEY"] = api_key # LiteLLM uses this for many providers

    # --- AI Identity Setup ---
    console.print(Panel("Now, let's define who I am. Describe my personality, goals, and core directives.", title="[bold cyan]Step 1: My Identity (ai.md)[/bold cyan]", border_style="cyan"))
    ai_persona_prompt = Prompt.ask(
        "[yellow]Describe me[/yellow]",
        default="You are IronClaw, a helpful and diligent AI assistant. Your goal is to assist the user with tasks by using tools and accessing information. You are concise and direct."
    )
    save_file(AI_IDENTITY_PATH, ai_persona_prompt)
    console.print(f"[green]✔ AI identity saved to {AI_IDENTITY_PATH}[/green]\n")

    # --- User Identity Setup ---
    console.print(Panel("Next, tell me about yourself. What are your goals, preferences, or any other relevant information?", title="[bold cyan]Step 2: Your Profile (user.md)[/bold cyan]", border_style="cyan"))
    user_profile_prompt = Prompt.ask(
        "[yellow]Describe yourself[/yellow]",
        default="The user is a software developer working on a project named 'IronClaw'."
    )
    save_file(USER_IDENTITY_PATH, user_profile_prompt)
    console.print(f"[green]✔ User profile saved to {USER_IDENTITY_PATH}[/green]\n")

    # --- Final Configuration ---
    console.print(Panel("Finally, let's give this agent a name.", title="[bold cyan]Step 3: Agent Name[/bold cyan]", border_style="cyan"))
    agent_name = Prompt.ask("What should I call this agent instance?", default="IronClaw-1")

    config = {
        "agent_name": agent_name,
        "llm": {
            "provider": "openai", # Default, user can change later
            "model": "gpt-4o",
            "api_key": api_key # Note: Storing keys in config is not best practice but follows spec.
        },
        "channels": {} # Channels are configured separately now.
    }
    save_file(CONFIG_PATH, json.dumps(config, indent=4))
    console.print(f"[green]✔ Main configuration saved to {CONFIG_PATH}[/green]\n")

    console.rule("[bold green]Setup Complete![/bold green]")
    console.print("You can now configure channels and run the agent using [bold cyan]python main.py[/bold cyan].")

if __name__ == "__main__":
    run_ai_wizard()
