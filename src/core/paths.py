from pathlib import Path

# The root directory for all user-specific data, configs, and .env file.
# ~/.iron_claw/
BASE_DIR = Path.home() / ".iron_claw"

# ~/.iron_claw/.env
ENV_PATH = BASE_DIR / ".env"

# ~/.iron_claw/data/
DATA_ROOT = Path.home() / ".iron_claw_data"

# ~/.iron_claw/data/plugins/
PLUGINS_DIR = DATA_ROOT / "plugins"

# ~/.iron_claw/data/channels/
CHANNELS_DIR = DATA_ROOT / "channels"

# ~/.iron_claw/data/config.json
CONFIG_PATH = DATA_ROOT / "config.json"

# ~/.iron_claw/data/identity/
IDENTITY_DIR = DATA_ROOT / "identity"

# ~/.iron_claw/data/memory/
MEMORY_DIR = DATA_ROOT / "memory"

# ~/.iron_claw/data/memory/history.json
HISTORY_PATH = MEMORY_DIR / "history.json"

# ~/.iron_claw/data/memory/messages.json
MESSAGES_PATH = MEMORY_DIR / "messages.json"

# Project root, for project-level files like providers.json
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# /path/to/project/providers.json
PROVIDERS_JSON_PATH = PROJECT_ROOT / "providers.json"

# /path/to/project/src/custom
CUSTOM_PLUGINS_DIR = PROJECT_ROOT / "src" / "custom"

"""Create all necessary directories if they don't exist."""
BASE_DIR.mkdir(exist_ok=True)
DATA_ROOT.mkdir(exist_ok=True)
PLUGINS_DIR.mkdir(exist_ok=True)
CHANNELS_DIR.mkdir(exist_ok=True)
IDENTITY_DIR.mkdir(exist_ok=True)
MEMORY_DIR.mkdir(exist_ok=True)
