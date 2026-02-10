from typing import List
from pydantic import Field
from src.core.interfaces import ComponentConfig

class BashToolConfig(ComponentConfig):
    enabled: bool = Field(True, description="Whether the Bash execution tool is active.")
    safe_commands: List[str] = Field(
        ["ls", "pwd", "echo", "whoami", "date", "uname", "df", "du", "free", "uptime", "ironclaw", "cat"],
        description="List of commands that are considered safe to execute without extra confirmation."
    )
    timeout_seconds: int = Field(15, description="Maximum time (in seconds) a command is allowed to run.")
