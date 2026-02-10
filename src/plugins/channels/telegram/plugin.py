import asyncio
import re
from functools import partial
from typing import Any, Tuple, TYPE_CHECKING

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramUnauthorizedError
from rich.console import Console

from src.core.interfaces import BaseChannel
from .config import TelegramConfig

if TYPE_CHECKING:
    from src.core.ai.router import Router

console = Console()

TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TYPING_INTERVAL_SECONDS = 4.5

class TelegramChannel(BaseChannel[TelegramConfig]):
    """
    A production-ready channel for interacting with an AI agent via a Telegram Bot.
    This bot is designed to serve a single admin user.
    """
    name = "telegram"
    config_class = TelegramConfig

    def __init__(self):
        super().__init__()
        self.bot: Bot | None = None
        self.admin_id: int | None = None

    async def healthcheck(self) -> Tuple[bool, str]:
        """Checks if the bot token and admin ID are valid."""
        if not self.config.bot_token:
            return False, "Telegram Bot Token is not set."
        if not self.config.admin_id:
            return False, "Telegram Admin ID is not set."

        try:
            temp_bot = Bot(token=self.config.bot_token)
            bot_user = await temp_bot.get_me()
            await temp_bot.session.close()
            return True, f"OK (Bot: @{bot_user.username})"
        except TelegramUnauthorizedError:
            return False, "Telegram Bot Token is invalid or expired."
        except Exception as e:
            return False, f"An unexpected error occurred during Telegram health check: {e}"

    async def start(self, router: "Router"):
        """Initializes and starts the Telegram bot's polling loop."""
        if not self.config.enabled:
            return

        try:
            self.admin_id = int(self.config.admin_id)
        except ValueError:
            console.print(f"[bold red]Invalid Admin ID for Telegram: {self.config.admin_id}[/bold red]")
            return

        self.bot = Bot(token=self.config.bot_token)
        dp = Dispatcher()

        dp.message(CommandStart())(self._handle_start)
        dp.message(F.text)(partial(self._handle_text, router=router))
        dp.message(F.photo)(partial(self._handle_photo, router=router))
        dp.message(F.document)(partial(self._handle_document, router=router))

        console.print(f"Starting Telegram bot for admin user {self.admin_id}.")
        try:
            await dp.start_polling(self.bot)
        except Exception as e:
            console.print(f"[bold red]Fatal error starting Telegram bot: {e}[/bold red]")

    async def _is_user_allowed(self, message: types.Message) -> bool:
        """Checks if the message is from the configured admin user."""
        if not message.from_user or message.from_user.id != self.admin_id:
            if message.from_user:
                console.print(f"[yellow]Unauthorized access attempt by user {message.from_user.id} (@{message.from_user.username}).[/yellow]")
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
            await router.process_message(text_to_process, "telegram", str(message.chat.id))
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

    def _escape_markdown(self, text: str) -> str:
        """Escapes reserved characters for Telegram MarkdownV2."""
        # Reserved characters: _ * [ ] ( ) ~ ` > # + - = | { } . !
        return re.sub(r"([_*\\~\\`>#+\-=|{}.!])", r"\\\1", text)

    async def send_message(self, text: str, target: str | None = None):
        """Sends a message to the target user."""
        if not self.bot:
            console.print("[bold red]Cannot send message, bot is not initialized.[/bold red]")
            return
        
        target_id = target or self.config.admin_id
        if not target_id:
            console.print("[bold red]No target ID provided for Telegram message.[/bold red]")
            return
        # check if its a tool call or tool result and format markdown
        if text.startswith("[Tool Result]") or text.startswith("[Calling tool]"):
            # Inside pre-formatted code blocks, only \ and ` need escaping
            escaped_content = text.replace("\\", "\\\\").replace("`", "\\`")
            text = f"```\n{escaped_content}\n```"
        else:
            # For standard text, escape all reserved characters to avoid parsing errors
            text = self._escape_markdown(text)
            
        await self._send_text_async(target_id, text)

    async def _send_text_async(self, user_id: str, text: str):
        """Asynchronously sends a text message, handling splitting."""
        if not self.bot: return

        try:
            chat_id = int(user_id)
        except ValueError:
            console.print(f"[bold red]Invalid target user_id for Telegram: {user_id}[/bold red]")
            return

        if len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH:
            await self.bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=True, parse_mode="MarkdownV2")
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
            try:
                await self.bot.send_message(chat_id=chat_id, text=part, disable_web_page_preview=True, parse_mode="MarkdownV2")
                await asyncio.sleep(0.5)
            except Exception as e:
                console.print(f"[bold red]Error sending Telegram message part: {e}[/bold red]")
