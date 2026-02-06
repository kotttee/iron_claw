import asyncio
import logging
from functools import partial
from typing import Any, Dict, Tuple, TYPE_CHECKING

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramUnauthorizedError

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

    @property
    def name(self) -> str:
        """The unique name of this channel."""
        return "telegram_bot"

    async def healthcheck(self) -> Tuple[bool, str]:
        """Checks if the bot token and admin ID are valid."""
        token = self._get_secret("TELEGRAM_BOT_TOKEN")
        admin_id_str = self._get_secret("TELEGRAM_ADMIN_ID")

        if not token:
            return False, "Telegram Bot Token is not set."
        if not admin_id_str:
            return False, "Telegram Admin ID is not set."

        try:
            temp_bot = Bot(token=token)
            bot_user = await temp_bot.get_me()
            await temp_bot.session.close() # Clean up the session
            return True, f"OK (Bot: @{bot_user.username})"
        except TelegramUnauthorizedError:
            return False, "Telegram Bot Token is invalid or expired."
        except Exception as e:
            return False, f"An unexpected error occurred during Telegram health check: {e}"

    def setup_wizard(self) -> None:
        """Interactively prompts for Telegram configuration for a single admin user."""
        from rich.console import Console
        from rich.prompt import Prompt
        console = Console()

        console.print("[bold blue]Configuring Telegram Bot Channel...[/bold blue]")
        console.print("You can get a token by talking to [bold magenta]@BotFather[/bold magenta] on Telegram.")
        token = Prompt.ask("Enter Telegram Bot Token", default=self._get_secret("TELEGRAM_BOT_TOKEN"))
        
        if token:
            self._save_secret("TELEGRAM_BOT_TOKEN", token)

        console.print("\nEnter the Telegram User ID of the admin who will use this bot.")
        console.print("You can find your ID by messaging [bold magenta]@userinfobot[/bold magenta].")
        admin_id_str = Prompt.ask("Admin User ID", default=self._get_secret("TELEGRAM_ADMIN_ID"))

        if admin_id_str:
            try:
                admin_id = int(admin_id_str.strip())
                self._save_secret("TELEGRAM_ADMIN_ID", str(admin_id))
                self.config["enabled"] = True
                self.save_config()
                console.print("✅ Telegram configured successfully.")
            except ValueError:
                console.print("[bold red]Error: Invalid User ID. Please enter a number only.[/bold red]")
                self.config["enabled"] = False
                self.save_config()
        else:
            self.config["enabled"] = False
            self.save_config()

    async def start(self, config: Dict[str, Any], router: "Router"):
        """Initializes and starts the Telegram bot's polling loop."""
        token = self._get_secret("TELEGRAM_BOT_TOKEN")
        admin_id_str = self._get_secret("TELEGRAM_ADMIN_ID")
        
        self.admin_id = int(admin_id_str)
        self.bot = Bot(token=token)
        dp = Dispatcher()

        dp.message(CommandStart())(self._handle_start)
        dp.message(F.text)(partial(self._handle_text, router=router))
        dp.message(F.photo)(partial(self._handle_photo, router=router))
        dp.message(F.document)(partial(self._handle_document, router=router))

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
            router.process_message(text_to_process, "telegram", str(message.chat.id))
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

        try:
            chat_id = int(user_id)
        except ValueError:
            logger.error(f"Invalid target user_id for Telegram: {user_id}")
            return

        if len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH:
            await self.bot.send_message(chat_id=chat_id, text=text)
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
            await self.bot.send_message(chat_id=chat_id, text=part)
            await asyncio.sleep(0.5)
