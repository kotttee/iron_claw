from typing import Any, Dict, TYPE_CHECKING

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from rich.console import Console
from rich.prompt import Prompt

from src.interfaces.channel import BaseChannel

if TYPE_CHECKING:
    from src.core.router import MessageRouter


class TelegramBotChannel(BaseChannel):
    """
    A channel for interacting with the AI agent via a Telegram Bot.
    """

    def __init__(self):
        self.bot: Bot | None = None

    @property
    def plugin_id(self) -> str:
        """The namespaced, unique identifier for this plugin."""
        return "channel/telegram_bot"

    def setup(self, wizard_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prompts the user for the Telegram Bot Token and personality.
        """
        console = Console()
        console.print(
            "[bold blue]Please provide your Telegram Bot Token.[/bold blue]"
        )
        console.print(
            "You can get this by talking to [bold magenta]@BotFather[/bold magenta] on Telegram."
        )
        token = Prompt.ask("Enter Telegram Bot Token")
        personality = Prompt.ask(
            "Set Agent Personality for this channel",
            default="A helpful assistant.",
        )
        return {"token": token, "personality": personality}

    async def start(self, config: Dict[str, Any], router: "MessageRouter"):
        """
        Starts the Telegram bot's polling loop.
        """
        token = config.get("token")
        if not token:
            print(f"Error: Telegram Bot Token not found for '{self.plugin_id}'. Skipping.")
            return

        self.bot = Bot(token=token)
        dp = Dispatcher()

        @dp.message(CommandStart())
        async def send_welcome(message: types.Message):
            await message.reply("IronClaw agent connected. How can I help you?")

        @dp.message()
        async def handle_message(message: types.Message):
            if message.text:
                user_id = str(message.chat.id)
                # Pass the full context to the router
                await router.route_message(self, user_id, message.text)

        try:
            await dp.start_polling(self.bot)
        except Exception as e:
            print(f"Error starting Telegram bot '{self.plugin_id}': {e}")

    async def send_reply(self, user_id: str, text: str):
        """Sends a reply back to the user on Telegram."""
        if self.bot:
            await self.bot.send_message(chat_id=user_id, text=text)
        else:
            print(f"Error: Attempted to send message via '{self.plugin_id}' but bot is not initialized.")
