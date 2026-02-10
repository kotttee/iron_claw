import subprocess
from src.core.interfaces import BaseTool
from .config import BashToolConfig

class ExecuteBashTool(BaseTool[BashToolConfig]):
    """
    A tool for executing safe, non-interactive bash commands.
    """
    name = "system/bash"
    config_class = BashToolConfig

    async def execute(self, command: str) -> str:
        """Executes a shell command from a safelist and returns its output."""
        command_parts = command.strip().split()
        if command_parts[0] not in self.config.safe_commands:
            return f"Error: Command '{command_parts[0]}' is not allowed. Allowed commands are: {', '.join(self.config.safe_commands)}."

        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
            )
            
            output = f"STDOUT:\n{result.stdout.strip()}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr.strip()}"
            return output

        except subprocess.CalledProcessError as e:
            return f"Error executing command '{command}':\nExit Code: {e.returncode}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
        except subprocess.TimeoutExpired:
            return f"Error: Command '{command}' timed out after {self.config.timeout_seconds} seconds."
        except Exception as e:
            return f"An unexpected error occurred while executing '{command}': {e}"

    def format_output(self, result: str) -> str:
        if result.startswith("Error"):
            return f"⚠️ {result}"
        return f"⚙️ Command executed. Total output length: {len(result)} characters."

    async def healthcheck(self): return True, "OK"
