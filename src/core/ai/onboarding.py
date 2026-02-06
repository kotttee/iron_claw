import json
from rich.console import Console
from rich.markdown import Markdown

from src.core.kernel import Kernel
from src.core.ai.identity_manager import IdentityManager
from src.core.ai.settings import SettingsManager

console = Console()

SYSTEM_PROMPT = """
You are the IronClaw Architect. Your goal is to establish the AI's identity, the user's profile, and system preferences.

**Phase 1: AI Persona.** Interview the user to define your own persona. Ask about your name, your tone (e.g., Sarcastic, Professional), and your interaction style.
**Phase 2: User Profile.** Ask the user about their name, their goals, and their technical expertise.
**Phase 3: System Preferences.** Ask the user about their preferences, such as timezone and verbosity. Format the output as a Markdown list.

**Final Action:**
Once you have a clear understanding of all three, output the special command:
`###SAVE_IDENTITY### | {"ai_persona": "...", "user_profile": "...", "preferences": "..."}`
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
    kernel.router.context_manager.add_message("system", SYSTEM_PROMPT)

    # AI starts the conversation
    initial_response = "Hello! I'm the IronClaw Architect, ready to get set up. To start, let's define my persona. What would you like to name me?"
    console.print(Markdown(initial_response))
    kernel.router.context_manager.add_message("assistant", initial_response)

    while True:
        try:
            user_input = console.input("You > ")
            if user_input.lower() in ["exit", "quit"]:
                break

            kernel.router.context_manager.add_message("user", user_input)
            response = kernel.router.provider.chat(kernel.router.context_manager.messages)
            kernel.router.context_manager.add_message("assistant", response)

            if "###SAVE_IDENTITY###" in response:
                console.print("[bold yellow]Identity save command detected. Processing...[/bold yellow]")
                try:
                    command_part = response.split("###SAVE_IDENTITY### |", 1)[1].strip()
                    identity_data = json.loads(command_part)
                    ai_persona = identity_data.get("ai_persona")
                    user_profile = identity_data.get("user_profile")
                    preferences = identity_data.get("preferences")

                    if not ai_persona or not user_profile or not preferences:
                        console.print("[bold red]Error: Invalid data. 'ai_persona', 'user_profile', or 'preferences' missing.[/bold red]")
                        continue

                    # Use the existing IdentityManager to save the markdown files
                    identity_manager = IdentityManager()
                    result = identity_manager.run(ai_persona, user_profile, preferences)
                    console.print(f"[bold green]{result}[/bold green]")
                    
                    console.print("Onboarding complete. You can now use 'ironclaw talk'.")
                    break
                except (json.JSONDecodeError, IndexError) as e:
                    console.print(f"[bold red]Error parsing identity data: {e}[/bold red]")
                    kernel.router.context_manager.messages.pop() # Let the model try again
                    continue
            else:
                console.print(Markdown(response))

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Onboarding interrupted. Exiting.[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
            break
