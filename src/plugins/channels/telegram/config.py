from pydantic import Field
from src.core.interfaces import ComponentConfig

class TelegramConfig(ComponentConfig):
    enabled: bool = Field(False, description="Whether the Telegram bot channel is active.")
    bot_token: str = Field("", description="The Telegram Bot Token from @BotFather.")
    admin_id: str = Field("", description="The Telegram User ID of the admin who will use this bot.")
