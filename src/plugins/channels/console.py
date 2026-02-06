import asyncio
from typing import Any, Dict, TYPE_CHECKING

from rich.console import Console
from rich.prompt import Prompt

from src.interfaces.channel import BaseChannel
from src.core.interfaces import ConfigurablePlugin

if TYPE_CHECKING:
    from src.core.ai.router import Router


class ConsoleChannel(BaseChannel, ConfigurablePlugin):
    """
    A channel for interacting with the AI agent via the command line.
    """

    def __init__(self):
        super().__init__(name="console", category="channel")

    @property
    def plugin_id(self) -> str:
        return "console"

    def setup_wizard(self) -> None:
        """
        The console channel prompts for an agent personality.
        """
        console = Console()
        console.print("[bold green]Console channel enabled.[/bold green]")
        personality = Prompt.ask(
            "Set Agent Personality for this channel",
            default="A helpful assistant.",
        )
        self.config["personality"] = personality
        self.save_config()

    def is_enabled(self) -> bool:
        """Console is always enabled."""
        return True

    async def start(self, config: Dict[str, Any], router: "Router"):
        """
        Starts the console interaction loop.
        """
        console = Console()
        console.print(f"[bold blue]Starting console channel...[/bold blue]")
        console.print(f"Agent Personality: {self.config.get('personality', 'Not set')}")

        while True:
            try:
                user_input = await asyncio.to_thread(
                    Prompt.ask, "[bold yellow]You[/bold yellow]"
                )
                if user_input.lower() in ["exit", "quit"]:
                    break
                router.process_message(user_input, "console")
            except (KeyboardInterrupt, EOFError):
                break
        
        console.print("\n[bold red]Exiting console channel.[/bold red]")

    async def send_reply(self, user_id: str, text: str):
        """Sends a reply back to the console."""
        # user_id is ignored for a single-user console channel
        console = Console()
        console.print(f"[bold red]Agent[/bold red]: {text}")

    def setup(self, wizard_context: Dict[str, Any]) -> Dict[str, Any]:
        # This method is required by BaseChannel, but we use setup_wizard.
        # We can leave it empty or raise a NotImplementedError if it's not supposed to be called.
        # For now, we'll just return the config.
        return self.config
