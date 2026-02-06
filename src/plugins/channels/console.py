import os
from typing import Any, Dict, Tuple, TYPE_CHECKING

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from src.core.ai.identity import IdentityManager
from src.interfaces.channel import BaseChannel
from src.core.interfaces import ConfigurablePlugin

if TYPE_CHECKING:
    from src.core.ai.router import Router

console = Console()

class ConsoleChannel(BaseChannel, ConfigurablePlugin):
    """
    The default channel for interacting with the agent via the command line.
    """

    def __init__(self):
        # The name is set here by the parent constructor
        super().__init__(name="console", category="channel")
        self.identity_manager = IdentityManager()

    def setup_wizard(self) -> None:
        """Console channel requires no setup."""
        console.print("The console channel is built-in and requires no configuration.")

    async def healthcheck(self) -> Tuple[bool, str]:
        """Console channel is always healthy."""
        return True, "OK"

    async def start(self, config: Dict[str, Any], router: "Router"):
        """The 'talk' command handles the console loop, so this method does nothing."""
        pass

    def send_message(self, text: str, target: str):
        """Prints the AI's reply to the console."""
        ai_name = self.identity_manager.get_ai_name()
        console.print(f"\n[bold cyan]{ai_name}:[/bold cyan]")
        console.print(Markdown(text))
