from pathlib import Path

# The root directory for all user-specific data, configs, and .env file.
# ~/.iron_claw/
BASE_DIR = Path.home() / ".iron_claw"

# ~/.iron_claw/.env
ENV_PATH = BASE_DIR / ".env"

# ~/.iron_claw/data/
DATA_ROOT = BASE_DIR / "data"

# ~/.iron_claw/data/configs/
CONFIGS_DIR = DATA_ROOT / "configs"

# ~/.iron_claw/data/identity/
IDENTITY_DIR = DATA_ROOT / "identity"

# ~/.iron_claw/data/memory.json
MEMORY_PATH = DATA_ROOT / "memory.json"

# Project root, for project-level files like providers.json
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# /path/to/project/providers.json
PROVIDERS_JSON_PATH = PROJECT_ROOT / "providers.json"

# /path/to/project/src/custom
CUSTOM_PLUGINS_DIR = PROJECT_ROOT / "src" / "custom"

def ensure_dirs():
    """Create all necessary directories if they don't exist."""
    BASE_DIR.mkdir(exist_ok=True)
    DATA_ROOT.mkdir(exist_ok=True)
    CONFIGS_DIR.mkdir(exist_ok=True)
    IDENTITY_DIR.mkdir(exist_ok=True)
