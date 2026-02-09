from typing import List
from src.core.interfaces import ComponentConfig

class BashToolConfig(ComponentConfig):
    safe_commands: List[str] = ["ls", "pwd", "echo", "whoami", "date", "uname", "df", "du", "free", "uptime"]
    timeout_seconds: int = 15
