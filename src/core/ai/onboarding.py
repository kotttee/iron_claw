import json
from rich.console import Console
from rich.markdown import Markdown

from src.core.kernel import Kernel
from src.core.ai.identity_manager import IdentityManager
from src.core.ai.settings import SettingsManager

console = Console()

SYSTEM_PROMPT = """
You are the IronClaw Architect. Your goal is to establish the AI's identity and the user's profile.

**Phase 1: AI Persona.** Interview the user to define your own persona. Ask about your name, your tone (e.g., Sarcastic, Professional), and your interaction style.
**Phase 2: User Profile.** Ask the user about their name, their goals, and their technical expertise.

**Final Action:**
Once you have a clear understanding of both, output the special command:
`###SAVE_IDENTITY### | {"ai_persona": "...", "user_profile": "..."}`
"""

def run_onboarding_session():
    """
    Runs the full onboarding process, including provider setup and conversational identity configuration.
    """
    settings_manager = SettingsManager()

    # Step 1: Ensure provider is configured.
    if not settings_manager.is_provider_configured():
        console.print("[bold yellow]Provider not configured. Starting setup wizard...[/bold yellow]")
        settings_manager.run_full_setup()
        if not settings_manager.is_provider_configured():
            console.print("[bold red]Provider setup is required to continue. Aborting onboarding.[/bold red]")
            return

    # Step 2: Conversational setup for AI persona and user profile.
    console.rule("[bold blue]Conversational Onboarding[/bold blue]")
    console.print("Let's set up the AI's identity and your user profile through a quick chat.")
    
    kernel = Kernel()
    kernel.context_manager.add_message("system", SYSTEM_PROMPT)

    while True:
        try:
            user_input = console.input("You > ")
            if user_input.lower() in ["exit", "quit"]:
                break

            kernel.context_manager.add_message("user", user_input)
            response = kernel.provider.chat(kernel.context_manager.get_messages())
            kernel.context_manager.add_message("assistant", response)

            if "###SAVE_IDENTITY###" in response:
                console.print("[bold yellow]Identity save command detected. Processing...[/bold yellow]")
                try:
                    command_part = response.split("###SAVE_IDENTITY### |", 1)[1].strip()
                    identity_data = json.loads(command_part)
                    ai_persona = identity_data.get("ai_persona")
                    user_profile = identity_data.get("user_profile")

                    if not ai_persona or not user_profile:
                        console.print("[bold red]Error: Invalid data. 'ai_persona' or 'user_profile' missing.[/bold red]")
                        continue

                    # Use the existing IdentityManager to save the markdown files
                    identity_manager = IdentityManager()
                    # We pass an empty string for preferences as it's now handled by SettingsManager
                    result = identity_manager.run(ai_persona, user_profile, "") 
                    console.print(f"[bold green]{result}[/bold green]")
                    
                    console.print("Onboarding complete. You can now use 'ironclaw talk'.")
                    break
                except (json.JSONDecodeError, IndexError) as e:
                    console.print(f"[bold red]Error parsing identity data: {e}[/bold red]")
                    kernel.context_manager.messages.pop() # Let the model try again
                    continue
            else:
                console.print(Markdown(response))

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Onboarding interrupted. Exiting.[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
            break
