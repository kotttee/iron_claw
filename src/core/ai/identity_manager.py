from pathlib import Path

class IdentityManager:
    """
    Manages the AI's and user's identity files.
    """
    def __init__(self, base_dir: Path | str = "data/identity"):
        self.base_dir = Path(base_dir)

    def save_identity(self, ai_persona: str, user_profile: str) -> str:
        """
        Writes the AI persona and user profile to their respective files.
        """
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            (self.base_dir / "ai.md").write_text(ai_persona, encoding="utf-8")
            (self.base_dir / "user.md").write_text(user_profile, encoding="utf-8")
            return "✅ Identity saved successfully."
        except Exception as e:
            return f"Error saving identity: {e}"

    def load_identity(self) -> tuple[str | None, str | None]:
        """
        Loads the AI persona and user profile from their files.
        """
        ai_persona = None
        user_profile = None
        try:
            ai_path = self.base_dir / "ai.md"
            if ai_path.exists():
                ai_persona = ai_path.read_text(encoding="utf-8")
            user_path = self.base_dir / "user.md"
            if user_path.exists():
                user_profile = user_path.read_text(encoding="utf-8")
        except Exception:
            # Return None if any error occurs
            pass
        return ai_persona, user_profile
