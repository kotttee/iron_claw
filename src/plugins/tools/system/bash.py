import subprocess
from typing import Type

from pydantic import BaseModel, Field

from src.interfaces.tool import BaseTool

class ExecuteBashArgs(BaseModel):
    command: str = Field(..., description="The bash command to execute. Must be from the allowed list.")

class ExecuteBashTool(BaseTool):
    """
    A tool for executing safe, non-interactive bash commands.
    """
    @property
    def name(self) -> str:
        # The name now reflects its location, providing a namespace.
        return "system/bash"

    @property
    def description(self) -> str:
        return "Executes a safe, non-interactive bash command and returns its output. Useful for checking system state."

    @property
    def args_schema(self) -> Type[BaseModel]:
        return ExecuteBashArgs

    def execute(self, command: str) -> str:
        """Executes a shell command from a safelist and returns its output."""
        safe_commands = ["ls", "pwd", "echo", "whoami", "date", "uname", "df", "du", "free", "uptime"]
        
        command_parts = command.strip().split()
        if not command_parts or command_parts[0] not in safe_commands:
            return f"Error: Command '{command_parts[0]}' is not allowed. Allowed commands are: {', '.join(safe_commands)}."

        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            
            output = f"STDOUT:\n{result.stdout.strip()}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr.strip()}"
            return output

        except subprocess.CalledProcessError as e:
            return f"Error executing command '{command}':\nExit Code: {e.returncode}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
        except subprocess.TimeoutExpired:
            return f"Error: Command '{command}' timed out after 15 seconds."
        except Exception as e:
            return f"An unexpected error occurred while executing '{command}': {e}"
