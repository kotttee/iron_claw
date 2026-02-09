import json
from rich.console import Console
from rich.markdown import Markdown
from src.core.ai.router import Router
from src.core.ai.settings import SettingsManager

console = Console()

SYSTEM_PROMPT = """
You are the IronClaw Architect. Your goal is to establish the AI's identity, the user's profile, and system preferences.

**Phase 1: AI Persona.** Interview the user to define your own persona (name, tone, style).
**Phase 2: User Profile.** Ask the user about their name and goals.
**Phase 3: System Preferences.** Ask about preferences (verbosity, etc.).

**Final Action:**
Once complete, output the special command:
`###SAVE_IDENTITY### | {"name": "AI Name", "persona": "Persona description", "user_goals": "User goals", "preferences": {"key": "value"}}`
"""

def run_onboarding_session():
    settings_manager = SettingsManager()
    if not settings_manager.is_provider_configured():
        settings_manager.run_full_setup()

    router = Router()
    console.rule("[bold blue]Conversational Onboarding[/bold blue]")
    
    messages = []
    initial_response = router.provider.chat(
        model=router.model_name,
        messages=[],
        system_prompt=SYSTEM_PROMPT
    )
    console.print(Markdown(initial_response))
    messages.append({"role": "assistant", "content": initial_response})

    while True:
        try:
            user_input = console.input("You > ")
            if user_input.lower() in ["exit", "quit"]: break
            messages.append({"role": "user", "content": user_input})
            
            response = router.provider.chat(
                model=router.model_name,
                messages=messages,
                system_prompt=SYSTEM_PROMPT
            )
            messages.append({"role": "assistant", "content": response})

            if "###SAVE_IDENTITY###" in response:
                try:
                    data_str = response.split("###SAVE_IDENTITY### |", 1)[1].strip()
                    data = json.loads(data_str)
                    router.memory.update_config(data)
                    console.print("[bold green]Identity saved successfully! Use ironclaw talk to start a chat session or ironclaw config to update settings.[/bold green]")
                    break
                except Exception as e:
                    console.print(f"[bold red]Error saving identity: {e}[/bold red]")
            else:
                console.print(Markdown(response))
        except KeyboardInterrupt:
            break
