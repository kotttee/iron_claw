from pathlib import Path

# Define paths relative to this file's location
DATA_ROOT = Path(__file__).parent.parent.parent / "data"
IDENTITY_DIR = DATA_ROOT / "identity"
AI_IDENTITY_PATH = IDENTITY_DIR / "ai.md"
USER_IDENTITY_PATH = IDENTITY_DIR / "user.md"

DEFAULT_AI_PROMPT = "You are a helpful AI assistant named IronClaw."
# A more generic default for when user.md is not set.
DEFAULT_USER_PROMPT = "You are assisting a user. Be helpful and responsive to their needs."

def get_system_prompt() -> str:
    """
    Constructs the system prompt by combining the AI and user identity files.
    Provides default prompts if the identity files are missing.
    """
    ai_prompt = DEFAULT_AI_PROMPT
    if AI_IDENTITY_PATH.exists():
        ai_prompt_text = AI_IDENTITY_PATH.read_text(encoding="utf-8").strip()
        if ai_prompt_text: # Ensure file is not empty
            ai_prompt = ai_prompt_text

    user_prompt = DEFAULT_USER_PROMPT
    if USER_IDENTITY_PATH.exists():
        user_prompt_text = USER_IDENTITY_PATH.read_text(encoding="utf-8").strip()
        if user_prompt_text: # Ensure file is not empty
            user_prompt = user_prompt_text

    # Combine the prompts into a single, well-structured system prompt
    system_prompt = f"""
# Your Identity and Role
{ai_prompt}

# Information About the User You Are Assisting
{user_prompt}
"""
    return system_prompt.strip()
