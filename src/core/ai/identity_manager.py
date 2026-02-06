from pathlib import Path

from src.core.paths import IDENTITY_DIR


class IdentityManager:
    """
    Manages the AI's persona, the user's profile, and preferences markdown files.
    """
    def __init__(self):
        self.identity_dir = IDENTITY_DIR
        self.ai_persona_path = self.identity_dir / "ai.md"
        self.user_profile_path = self.identity_dir / "user.md"
        self.preferences_path = self.identity_dir / "preferences.md"

    def run(self, ai_persona: str, user_profile: str, preferences: str) -> str:
        """
        Writes the AI persona, user profile, and preferences to their respective files.
        """
        try:
            self.identity_dir.mkdir(parents=True, exist_ok=True)
            self.ai_persona_path.write_text(ai_persona, encoding="utf-8")
            self.user_profile_path.write_text(user_profile, encoding="utf-8")
            self.preferences_path.write_text(preferences, encoding="utf-8")

            return "✅ AI Persona, User Profile, and Preferences saved successfully."
        except Exception as e:
            return f"Error saving identity files: {e}"

    @staticmethod
    def get_identity_prompt() -> str:
        """
        Loads the AI persona, user profile, and system preferences to form a combined prompt.
        """
        prompt_parts = []
        
        # Load AI Persona and User Profile from markdown files
        ai_persona_path = IDENTITY_DIR / "ai.md"
        if ai_persona_path.exists():
            ai_persona = ai_persona_path.read_text(encoding="utf-8").strip()
            if ai_persona:
                prompt_parts.append("=== AI PERSONA ===")
                prompt_parts.append(ai_persona)

        user_profile_path = IDENTITY_DIR / "user.md"
        if user_profile_path.exists():
            user_profile = user_profile_path.read_text(encoding="utf-8").strip()
            if user_profile:
                prompt_parts.append("=== USER PROFILE ===")
                prompt_parts.append(user_profile)

        # Load preferences from preferences.md
        preferences_path = IDENTITY_DIR / "preferences.md"
        if preferences_path.exists():
            preferences = preferences_path.read_text(encoding="utf-8").strip()
            if preferences:
                prompt_parts.append("=== SYSTEM PREFERENCES ===")
                prompt_parts.append(preferences)

        return "\n".join(prompt_parts)
