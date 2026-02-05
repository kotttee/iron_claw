import asyncio
from typing import Any, Dict, TYPE_CHECKING

from rich.console import Console
from rich.prompt import Prompt

from src.interfaces.channel import BaseChannel

if TYPE_CHECKING:
    from src.core.router import MessageRouter


class ConsoleChannel(BaseChannel):
    """
    A channel for interacting with the AI agent via the command line.
    """

    @property
    def plugin_id(self) -> str:
        return "channels/console"

    def setup(self, wizard_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        The console channel prompts for an agent personality.
        """
        console = Console()
        console.print("[bold green]Console channel enabled.[/bold green]")
        personality = Prompt.ask(
            "Set Agent Personality for this channel",
            default="A helpful assistant.",
        )
        return {"personality": personality}

    async def start(self, config: Dict[str, Any], router: "MessageRouter"):
        """
        Starts the console interaction loop.
        """
        console = Console()
        console.print(f"[bold blue]Starting console channel...[/bold blue]")
        console.print(f"Agent Personality: {config.get('personality', 'Not set')}")
        
        user_id = "console_user"

        while True:
            try:
                user_input = await asyncio.to_thread(
                    Prompt.ask, "[bold yellow]You[/bold yellow]"
                )
                if user_input.lower() in ["exit", "quit"]:
                    break
                await router.route_message(self, user_id, user_input)
            except (KeyboardInterrupt, EOFError):
                break
        
        console.print("\n[bold red]Exiting console channel.[/bold red]")

    async def send_reply(self, user_id: str, text: str):
        """Sends a reply back to the console."""
        # user_id is ignored for a single-user console channel
        console = Console()
        console.print(f"[bold red]Agent[/bold red]: {text}")
