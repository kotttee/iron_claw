from datetime import datetime
import pytz
from src.core.interfaces import BaseTool
from .config import DateTimeConfig

class GetCurrentDateTimeTool(BaseTool[DateTimeConfig]):
    """
    Returns the current date and time in a specified timezone.
    """
    name = "standard/get_current_datetime"
    config_class = DateTimeConfig

    async def execute(self, timezone: str = "UTC") -> str:
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            return f"Current date and time ({timezone}): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        except pytz.UnknownTimeZoneError:
            return f"Error: Unknown timezone '{timezone}'. Please use a valid timezone name."
        except Exception as e:
            return f"Error getting the current time: {e}"

    def format_output(self, result: str) -> str:
        if result.startswith("Error"):
            return f"⚠️ {result}"
        return f"🕒 {result}"

    async def healthcheck(self): return True, "OK"
