from typing import List
from pydantic import Field
from src.core.interfaces import ComponentConfig

class BashToolConfig(ComponentConfig):
    enabled: bool = Field(True, description="Whether the Bash execution tool is active.")
    safe_commands: List[str] = Field(
        ["ls", "pwd", "echo", "whoami", "date", "uname", "df", "du",
         "free", "uptime", "ironclaw", "cat", "curl", "wget", "python3", "pip3", "python", "pip",
         "npm", "node", "git", "grep", "find", "mkdir", "rmdir", "touch", "rm", "cp", "mv", "chmod",
         "chown", "ps", "top", "htop", "kill", "tar", "zip", "unzip", "ssh", "scp", "ping", "netstat", "ifconfig", "ip",
         "docker", "docker-compose", "kubectl", "gh", "brew", "apt", "apt-get", "yum", "dnf",
         "systemctl", "journalctl", "tail", "head", "less", "more", "sed", "awk", "xargs",
         "sort", "uniq", "wc", "diff", "patch", "history", "alias", "export", "env", "printenv"
        ],
        description="List of commands that are considered safe to execute without extra confirmation."
    )
    timeout_seconds: int = Field(15, description="Maximum time (in seconds) a command is allowed to run.")
