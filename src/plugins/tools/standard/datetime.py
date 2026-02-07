from datetime import datetime
import pytz
from rich.console import Console

console = Console()

class DateTimeTool:
    def __init__(self):
        self.name = "standard/get_current_datetime"
        self.description = "Returns the current date and time in a specified timezone."

    def run(self, timezone: str = "utc") -> str:
        """
        Returns the current date and time in the specified timezone.
        
        Args:
            timezone (str): The timezone to use, e.g., 'UTC', 'America/New_York'. Defaults to 'UTC'.
        
        Returns:
            str: The current date and time as a formatted string.
        """
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            return f"Current date and time ({timezone}): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        except pytz.UnknownTimeZoneError:
            return f"Error: Unknown timezone '{timezone}'. Please use a valid timezone name (e.g., 'UTC', 'Europe/London')."
        except Exception as e:
            console.print(f"[bold red]Error in datetime tool: {e}[/bold red]")
            return "Error getting the current time."

    def format_output(self, result: str) -> str:
        """Formats the raw result for user-facing output."""
        if result.startswith("Error"):
            return f"⚠️ {result}"
        return f"🕒 {result}"

def load():
    return DateTimeTool()
