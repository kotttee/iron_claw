from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

class BaseChannel(ABC):
    """
    Abstract Base Class for all channel plugins.

    A channel is a medium through which the AI agent interacts with the outside world,
    such as a console, a Telegram chat, or a Discord server.
    """

    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category

    @abstractmethod
    def setup_wizard(self) -> None:
        """
        Interactively prompts the user for configuration settings required by the channel.
        This method is called from the main CLI `config` command.
        """
        raise NotImplementedError

    @abstractmethod
    async def start(self, config: Dict[str, Any], router: 'Router'):
        """
        Starts the channel's main loop to listen for incoming messages.
        This method is called by the Kernel when the application starts.
        """
        raise NotImplementedError
        
    @abstractmethod
    def send_message(self, text: str, target: str):
        """
        Sends a reply back to the user on this channel.
        This method is called by the Router.
        """
        raise NotImplementedError

    @abstractmethod
    async def healthcheck(self) -> Tuple[bool, str]:
        """
        Performs a health check to ensure the channel is configured correctly and can connect.
        
        Returns:
            A tuple containing a boolean indicating health and a status message.
            (True, "OK") or (False, "Error message").
        """
        raise NotImplementedError
