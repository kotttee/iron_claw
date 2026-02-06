from rich.console import Console
from rich.markdown import Markdown
from src.interfaces.channel import BaseChannel

console = Console()

class ConsoleChannel(BaseChannel):
    """
    A simple channel for direct console interaction. This channel is used by the
    `talk` command and for direct output when the agent is run in the foreground.
    """
    def __init__(self):
        super().__init__(name="console", category="channel")

    async def start(self, *args, **kwargs):
        """The console channel is passive and doesn't need a running loop."""
        pass

    def send_message(self, text: str, target: str | None = None):
        """Prints the message to the console, formatted as Markdown."""
        console.print(Markdown(text))

    async def healthcheck(self):
        """The console channel is always healthy."""
        return True, "OK"

    def setup_wizard(self) -> None:
        """The console channel requires no setup."""
        pass
