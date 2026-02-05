from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseChannel(ABC):
    """
    Abstract Base Class for all channel plugins.

    A channel is a medium through which the AI agent interacts with the outside world,
    such as a console, a Telegram chat, or a Discord server.
    """

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """
        A unique identifier for the plugin (e.g., 'console', 'telegram').
        This should be a lowercase string with no spaces.
        """
        raise NotImplementedError

    @abstractmethod
    def setup(self, wizard_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interactively prompts the user for configuration settings required by the channel.

        This method is called by the setup wizard (`setup.py`) when the user chooses
        to enable this channel. It should use tools like `rich.prompt` to get
        necessary information, such as API tokens or personality settings.

        Args:
            wizard_context: A dictionary containing the global context of the setup wizard,
                            which can be used to access shared settings or state.

        Returns:
            A dictionary containing the configuration specific to this channel,
            which will be saved into the `data/config.json` file.
        """
        raise NotImplementedError

    @abstractmethod
    async def start(self, config: Dict[str, Any], router: 'MessageRouter'):
        """
        Starts the channel's main loop to listen for incoming messages.

        This method is called by the main application entry point (`main.py`)
        when the application starts.

        Args:
            config: The configuration dictionary for this specific channel,
                    loaded from `data/config.json`.
            router: The central message router to which incoming messages will be passed.
        """
        raise NotImplementedError
        
    @abstractmethod
    async def send_reply(self, user_id: str, text: str):
        """
        Sends a reply back to the user on this channel.

        Args:
            user_id: The identifier for the user or chat to send the reply to.
            text: The message to send.
        """
        raise NotImplementedError
