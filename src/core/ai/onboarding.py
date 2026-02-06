import json
from rich.console import Console
from rich.markdown import Markdown

from src.core.entities import Router
from src.core.ai.identity_manager import IdentityManager

console = Console()

SYSTEM_PROMPT = """
You are the IronClaw Architect. Your task is to interview the user to define two key profiles:
1.  **YOUR Persona:** This includes your name, your personality, your tone, and your style of interaction.
2.  **The USER'S Profile:** This includes their name, their primary goals, their technical expertise, and any other details that will help you assist them better.

Engage in a natural conversation to gather these details. When you are confident that you have a clear and detailed understanding of both profiles, you MUST output a special command to save the identity.

The command format is strict:
`###SAVE_IDENTITY### | {"ai_persona": "...", "user_profile": "..."}`

-   `ai_persona`: A detailed description of the AI's persona.
-   `user_profile`: A detailed description of the user's profile.

Do not output the `###SAVE_IDENTITY###` tag until you have gathered sufficient details and are ready to save.
"""


def run_onboarding_session():
    """
    Runs a conversational session to configure the AI and user identity.
    """
    router = Router()
    router.context_manager.add_message("system", SYSTEM_PROMPT)
    console.print(
        "[bold green]Welcome to IronClaw Onboarding![/bold green]"
    )
    console.print(
        "Let's set up your AI's identity and your user profile through a quick chat."
    )

    while True:
        try:
            user_input = console.input("You > ")
            if user_input.lower() in ["exit", "quit"]:
                break

            router.context_manager.add_message("user", user_input)
            response = router.provider.chat(
                router.context_manager.get_messages()
            )
            router.context_manager.add_message("assistant", response)

            if "###SAVE_IDENTITY###" in response:
                console.print("[bold yellow]Identity save command detected. Processing...[/bold yellow]")
                try:
                    command_part = response.split("###SAVE_IDENTITY### |", 1)[1].strip()
                    identity_data = json.loads(command_part)
                    ai_persona = identity_data.get("ai_persona")
                    user_profile = identity_data.get("user_profile")

                    if not ai_persona or not user_profile:
                        console.print("[bold red]Error: Invalid identity data. Missing 'ai_persona' or 'user_profile'.[/bold red]")
                        continue

                    identity_manager = IdentityManager()
                    result = identity_manager.save_identity(ai_persona, user_profile)
                    console.print(f"[bold green]{result}[/bold green]")
                    console.print("Onboarding complete. You can now use 'ironclaw talk'.")
                    break
                except (json.JSONDecodeError, IndexError) as e:
                    console.print(f"[bold red]Error parsing identity data: {e}[/bold red]")
                    console.print("[bold yellow]Please try again, ensuring the format is correct.[/bold yellow]")
                    # Remove the failed response from history to allow the model to retry
                    router.context_manager.messages.pop()
                    continue
            else:
                console.print(Markdown(response))

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Onboarding interrupted. Exiting.[/bold yellow]")
            break
