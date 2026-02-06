import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from rich.console import Console
from rich.prompt import Prompt

from src.interfaces.channel import BaseChannel
from src.core.interfaces import ConfigurablePlugin

if TYPE_CHECKING:
    from src.core.router import MessageRouter

# Configure logging for this specific module
logger = logging.getLogger(__name__)

# Constants
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TYPING_INTERVAL_SECONDS = 4.5


class TelegramBotChannel(BaseChannel, ConfigurablePlugin):
    """
    A production-ready channel for interacting with an AI agent via a Telegram Bot.
    """

    def __init__(self):
        super().__init__(name="telegram_bot", category="channel")
        self.bot: Bot | None = None
        self.allowed_users: List[int] = []
        self.console = Console()

    @property
    def plugin_id(self) -> str:
        """The namespaced, unique identifier for this plugin."""
        return "telegram_bot"

    def setup_wizard(self) -> None:
        """Interactively prompts for all necessary Telegram configuration."""
        self.console.print("[bold blue]Configuring Telegram Bot Channel...[/bold blue]")
        self.console.print("You can get a token by talking to [bold magenta]@BotFather[/bold magenta] on Telegram.")
        token = Prompt.ask("Enter Telegram Bot Token")
        if token:
            self._save_secret("TELEGRAM_BOT_TOKEN", token)

        self.console.print("\nEnter a comma-separated list of Telegram User IDs that are allowed to use this bot.")
        self.console.print("You can find your ID by messaging [bold magenta]@userinfobot[/bold magenta].")
        allowed_ids_str = Prompt.ask("Allowed User IDs (e.g., 12345678,87654321)")

        try:
            allowed_user_ids = [int(uid.strip()) for uid in allowed_ids_str.split(',') if uid.strip()]
        except ValueError:
            self.console.print("[bold red]Error: Invalid User IDs provided. Please enter numbers only.[/bold red]")
            allowed_user_ids = []

        personality = Prompt.ask("Set Agent Personality for this channel", default="A helpful assistant.")

        self.config["allowed_user_ids"] = allowed_user_ids
        self.config["personality"] = personality
        self.config["enabled"] = True
        self.save_config()
        self.console.print("✅ Telegram configured successfully.")

    async def start(self, config: Dict[str, Any], router: "MessageRouter"):
        """Initializes and starts the Telegram bot's polling loop."""
        token = self._get_secret("TELEGRAM_BOT_TOKEN")
        self.allowed_users = self.config.get("allowed_user_ids", [])

        if not token:
            logger.error(f"Telegram Bot Token not found for '{self.plugin_id}'. Skipping.")
            return
        if not self.allowed_users:
            logger.warning(f"No allowed users configured for '{self.plugin_id}'. The bot will not respond to anyone.")

        self.bot = Bot(token=token)
        dp = Dispatcher()

        # Register all handlers
        dp.message(CommandStart())(self._handle_start)
        dp.message(F.text)(lambda msg: self._handle_text(msg, router))
        dp.message(F.photo)(lambda msg: self._handle_photo(msg, router))
        dp.message(F.document)(lambda msg: self._handle_document(msg, router))

        logger.info(f"Starting Telegram bot '{self.plugin_id}' with {len(self.allowed_users)} allowed users.")
        try:
            await dp.start_polling(self.bot)
        except Exception as e:
            logger.critical(f"Fatal error starting Telegram bot '{self.plugin_id}': {e}", exc_info=True)

    async def _is_user_allowed(self, message: types.Message) -> bool:
        """Security Gatekeeper: Checks if the user is on the whitelist."""
        if not message.from_user or message.from_user.id not in self.allowed_users:
            logger.warning(
                f"Unauthorized access attempt by user {message.from_user.id if message.from_user else 'Unknown'} "
                f"(@{message.from_user.username if message.from_user else 'N/A'})."
            )
            return False
        return True

    async def _typing_loop(self, chat_id: int):
        """Sends a 'typing' status on a loop until the task is cancelled."""
        while True:
            try:
                if self.bot:
                    await self.bot.send_chat_action(chat_id, action=ChatAction.TYPING)
                await asyncio.sleep(TYPING_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in typing loop for chat {chat_id}: {e}")
                break

    async def _process_with_typing(self, message: types.Message, router: "MessageRouter", text_to_process: str):
        """Handles the core logic: whitelist check, typing indicator, and router call."""
        if not await self._is_user_allowed(message):
            return

        typing_task = asyncio.create_task(self._typing_loop(message.chat.id))
        try:
            await router.route_message(self, str(message.chat.id), text_to_process)
        finally:
            typing_task.cancel()

    # --- Message Handlers ---

    async def _handle_start(self, message: types.Message):
        if await self._is_user_allowed(message):
            await message.reply("IronClaw agent connected. How can I help you?")

    async def _handle_text(self, message: types.Message, router: "MessageRouter"):
        if message.text:
            await self._process_with_typing(message, router, message.text)

    async def _handle_photo(self, message: types.Message, router: "MessageRouter"):
        if message.photo:
            largest_photo = message.photo[-1]
            system_text = f"[SYSTEM EVENT: User sent a PHOTO. File ID: {largest_photo.file_id}]"
            await self._process_with_typing(message, router, system_text)

    async def _handle_document(self, message: types.Message, router: "MessageRouter"):
        if message.document:
            doc = message.document
            system_text = f"[SYSTEM EVENT: User sent a DOCUMENT. Filename: {doc.file_name}. File ID: {doc.file_id}]"
            await self._process_with_typing(message, router, system_text)

    # --- Outgoing Public Methods ---

    async def send_reply(self, user_id: str, text: str):
        """Splits long messages and sends them sequentially."""
        if not self.bot:
            logger.error("Cannot send reply, bot is not initialized.")
            return

        if len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH:
            await self.bot.send_message(chat_id=user_id, text=text)
            return

        # Smart Splitter Logic
        parts = []
        while len(text) > 0:
            if len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH:
                parts.append(text)
                break

            # Find the best place to split, prioritizing double newlines, then single.
            split_pos = text.rfind('\n\n', 0, TELEGRAM_MAX_MESSAGE_LENGTH)
            if split_pos == -1:
                split_pos = text.rfind('\n', 0, TELEGRAM_MAX_MESSAGE_LENGTH)
            if split_pos == -1:
                split_pos = TELEGRAM_MAX_MESSAGE_LENGTH

            parts.append(text[:split_pos])
            text = text[split_pos:].lstrip()

        for i, part in enumerate(parts):
            await self.bot.send_message(chat_id=user_id, text=part)
            if i < len(parts) - 1:
                await asyncio.sleep(0.5)  # Small delay between messages

    async def send_photo(self, user_id: str, file_path: str, caption: str = ""):
        """Sends a photo from a local path."""
        if not self.bot: return
        path = Path(file_path)
        if not path.is_file():
            logger.error(f"send_photo failed: File not found at {file_path}")
            await self.send_reply(user_id, f"[Agent Error: Could not find file at {path.name}]")
            return

        await self.bot.send_photo(user_id, photo=FSInputFile(path), caption=caption)

    async def send_file(self, user_id: str, file_path: str, caption: str = ""):
        """Sends a document from a local path."""
        if not self.bot: return
        path = Path(file_path)
        if not path.is_file():
            logger.error(f"send_file failed: File not found at {file_path}")
            await self.send_reply(user_id, f"[Agent Error: Could not find file at {path.name}]")
            return

        await self.bot.send_document(user_id, document=FSInputFile(path), caption=caption)

    # --- Public Download Helper ---

    async def download_file_by_id(self, file_id: str, destination_dir: str) -> str:
        """
        Downloads a file from Telegram using its file_id to a local directory.
        Returns the full path to the downloaded file.
        """
        if not self.bot:
            raise ConnectionError("Cannot download file, bot is not initialized.")

        dest_path = Path(destination_dir)
        dest_path.mkdir(parents=True, exist_ok=True)

        try:
            file_info = await self.bot.get_.file(file_id)
            if not file_info.file_path:
                raise FileNotFoundError("File path not available from Telegram.")

            # Construct a safe destination path
            original_filename = Path(file_info.file_path).name
            local_file_path = dest_path / original_filename

            await self.bot.download_file(file_info.file_path, destination=local_file_path)

            logger.info(f"Successfully downloaded file_id '{file_id}' to '{local_file_path}'")
            return str(local_file_path.resolve())
        except Exception as e:
            logger.error(f"Failed to download file_id '{file_id}': {e}", exc_info=True)
            raise

    def setup(self, wizard_context: Dict[str, Any]) -> Dict[str, Any]:
        # This method is required by BaseChannel, but we use setup_wizard.
        # We can leave it empty or raise a NotImplementedError if it's not supposed to be called.
        # For now, we'll just return the config.
        return self.config
