import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from rich.console import Console
from rich.prompt import Prompt

from src.interfaces.channel import BaseChannel
from src.core.interfaces import ConfigurablePlugin

if TYPE_CHECKING:
    from src.core.ai.router import Router

logger = logging.getLogger(__name__)

TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TYPING_INTERVAL_SECONDS = 4.5

class TelegramBotChannel(BaseChannel, ConfigurablePlugin):
    """
    A production-ready channel for interacting with an AI agent via a Telegram Bot.
    This bot is designed to serve a single admin user.
    """

    def __init__(self):
        super().__init__(name="telegram_bot", category="channel")
        self.bot: Bot | None = None
        self.admin_id: int | None = None
        self.console = Console()

    @property
    def plugin_id(self) -> str:
        """The namespaced, unique identifier for this plugin."""
        return "telegram_bot"

    def setup_wizard(self) -> None:
        """Interactively prompts for Telegram configuration for a single admin user."""
        self.console.print("[bold blue]Configuring Telegram Bot Channel...[/bold blue]")
        self.console.print("You can get a token by talking to [bold magenta]@BotFather[/bold magenta] on Telegram.")
        token = Prompt.ask("Enter Telegram Bot Token")
        if token:
            self._save_secret("TELEGRAM_BOT_TOKEN", token)

        self.console.print("\nEnter the Telegram User ID of the admin who will use this bot.")
        self.console.print("You can find your ID by messaging [bold magenta]@userinfobot[/bold magenta].")
        admin_id_str = Prompt.ask("Admin User ID")

        try:
            admin_id = int(admin_id_str.strip())
            self._save_secret("TELEGRAM_ADMIN_ID", str(admin_id))
        except ValueError:
            self.console.print("[bold red]Error: Invalid User ID. Please enter a number only.[/bold red]")
            return

        self.config["enabled"] = True
        self.save_config()
        self.console.print("✅ Telegram configured successfully for single admin user.")

    async def start(self, config: Dict[str, Any], router: "Router"):
        """Initializes and starts the Telegram bot's polling loop."""
        token = self._get_secret("TELEGRAM_BOT_TOKEN")
        admin_id_str = self._get_secret("TELEGRAM_ADMIN_ID")

        if not token:
            logger.error("Telegram Bot Token not found. Please run the setup wizard.")
            return
        if not admin_id_str:
            logger.error("Telegram Admin ID not found. Please run the setup wizard.")
            return

        self.admin_id = int(admin_id_str)
        self.bot = Bot(token=token)
        dp = Dispatcher()

        dp.message(CommandStart())(self._handle_start)
        dp.message(F.text)(lambda msg: self._handle_text(msg, router))
        dp.message(F.photo)(lambda msg: self._handle_photo(msg, router))
        dp.message(F.document)(lambda msg: self._handle_document(msg, router))

        logger.info(f"Starting Telegram bot for admin user {self.admin_id}.")
        try:
            await dp.start_polling(self.bot)
        except Exception as e:
            logger.critical(f"Fatal error starting Telegram bot: {e}", exc_info=True)

    async def _is_user_allowed(self, message: types.Message) -> bool:
        """Checks if the message is from the configured admin user."""
        if not message.from_user or message.from_user.id != self.admin_id:
            if message.from_user:
                logger.warning(f"Unauthorized access attempt by user {message.from_user.id} (@{message.from_user.username}).")
            return False
        return True

    async def _typing_loop(self, chat_id: int):
        """Sends a 'typing' status on a loop."""
        while True:
            try:
                if self.bot:
                    await self.bot.send_chat_action(chat_id, action=ChatAction.TYPING)
                await asyncio.sleep(TYPING_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception:
                break

    async def _process_with_typing(self, message: types.Message, router: "Router", text_to_process: str):
        """Handles whitelist check, typing indicator, and router call."""
        if not await self._is_user_allowed(message):
            return

        typing_task = asyncio.create_task(self._typing_loop(message.chat.id))
        try:
            # This call is now synchronous in the router
            router.process_message(text_to_process, "telegram")
        finally:
            typing_task.cancel()

    async def _handle_start(self, message: types.Message):
        if await self._is_user_allowed(message):
            await message.reply("IronClaw agent connected. How can I help you?")

    async def _handle_text(self, message: types.Message, router: "Router"):
        if message.text:
            await self._process_with_typing(message, router, message.text)

    async def _handle_photo(self, message: types.Message, router: "Router"):
        if message.photo:
            largest_photo = message.photo[-1]
            system_text = f"[SYSTEM EVENT: User sent a PHOTO. File ID: {largest_photo.file_id}]"
            await self._process_with_typing(message, router, system_text)

    async def _handle_document(self, message: types.Message, router: "Router"):
        if message.document:
            doc = message.document
            system_text = f"[SYSTEM EVENT: User sent a DOCUMENT. Filename: {doc.file_name}. File ID: {doc.file_id}]"
            await self._process_with_typing(message, router, system_text)

    def send_reply(self, text: str, target: str):
        """Sends a message to the target user. Required by the Router."""
        if not self.bot:
            logger.error("Cannot send message, bot is not initialized.")
            return
        
        asyncio.create_task(self._send_text_async(target, text))

    async def _send_text_async(self, user_id: str, text: str):
        """Asynchronously sends a text message, handling splitting."""
        if not self.bot: return

        if len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH:
            await self.bot.send_message(chat_id=user_id, text=text)
            return

        parts = []
        while len(text) > 0:
            if len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH:
                parts.append(text)
                break
            split_pos = text.rfind('\n\n', 0, TELEGRAM_MAX_MESSAGE_LENGTH)
            if split_pos == -1:
                split_pos = text.rfind('\n', 0, TELEGRAM_MAX_MESSAGE_LENGTH)
            if split_pos == -1:
                split_pos = TELEGRAM_MAX_MESSAGE_LENGTH
            parts.append(text[:split_pos])
            text = text[split_pos:].lstrip()

        for part in parts:
            await self.bot.send_message(chat_id=user_id, text=part)
            await asyncio.sleep(0.5)

    def setup(self, wizard_context: Dict[str, Any]) -> Dict[str, Any]:
        return self.config
