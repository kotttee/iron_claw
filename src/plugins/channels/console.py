import os
from typing import Any, Dict, TYPE_CHECKING

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from src.core.ai.identity import IdentityManager
from src.interfaces.channel import BaseChannel

if TYPE_CHECKING:
    from src.core.ai.router import Router

console = Console()

class ConsoleChannel(BaseChannel):
    """
    The default channel for interacting with the agent via the command line.
    """

    def __init__(self):
        super().__init__(name="console", category="channel")
        self.identity_manager = IdentityManager()

    async def start(self, config: Dict[str, Any], router: "Router"):
        """Starts the interactive console loop."""
        os.system("cls" if os.name == "nt" else "clear")
        
        ai_name = self.identity_manager.get_ai_name()
        user_name = self.identity_manager.get_user_name()

        console.print(
            Panel(
                f"Live Chat with {ai_name} | Press Ctrl+C to Exit",
                title="[bold green]🗣️ IronClaw Terminal[/bold green]",
                expand=False,
            )
        )
        console.print(f"[dim]You are {user_name}.[/dim]\n")

        while True:
            try:
                user_input = console.input(f"{user_name} > ")
                if not user_input.strip():
                    continue

                with console.status("[yellow]Thinking...[/yellow]", spinner="dots"):
                    # The router now handles the full processing flow
                    router.process_message(user_input, source="console")

            except (KeyboardInterrupt, EOFError):
                break
        
        console.print("\n[bold yellow]Exiting chat mode.[/bold yellow]")

    def send_reply(self, text: str, target: str):
        """Prints the AI's reply to the console."""
        ai_name = self.identity_manager.get_ai_name()
        console.print(f"[bold cyan]{ai_name}:[/bold cyan]")
        console.print(Markdown(text))
