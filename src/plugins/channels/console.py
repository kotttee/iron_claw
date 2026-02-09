from rich.console import Console
from rich.markdown import Markdown
from pydantic import BaseModel
from src.core.interfaces import BaseChannel

console = Console()

class ConsoleConfig(BaseModel):
    enabled: bool = True

class ConsoleChannel(BaseChannel[ConsoleConfig]):
    """
    A simple channel for direct console interaction.
    """
    name = "console"
    config_class = ConsoleConfig

    async def start(self, router):
        """The console channel is passive."""
        pass

    async def send_message(self, text: str, target: str | None = None):
        """Prints the message to the console, formatted as Markdown."""
        console.print(Markdown(text))

    async def healthcheck(self) -> tuple[bool, str]:
        """The console channel is always healthy."""
        return True, "OK"
