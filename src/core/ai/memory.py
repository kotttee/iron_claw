import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from src.core.interfaces import BaseComponent, ComponentConfig
from src.core.paths import PLUGINS_DIR

class AgentProfile(ComponentConfig):
    enabled: bool = Field(True, description="Whether the memory system is active.")
    bio: str = Field(
        "# Identity\n- Name: IronClaw\n- Role: Assistant\n\n# User\n- Name: User\n\n# Settings\n- Timezone: UTC", 
        description="Full identity, user persona, and preferences in Markdown format."
    )

class MemoryManager(BaseComponent[AgentProfile]):
    """
    Memory system for the AI.
    Handles chat history, long-term facts, and agent profile.
    """
    name = "memory"
    config_class = AgentProfile

    def __init__(self):
        super().__init__()
        self._init_db()

    def _init_db(self):
        cursor = self.db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.commit()

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO history (role, content, metadata) VALUES (?, ?, ?)",
            (role, content, json.dumps(metadata or {}))
        )
        self.db.commit()

    def get_short_term_context(self, limit: int = 50) -> List[Dict[str, str]]:
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT role, content FROM history ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def add_fact(self, fact: str):
        cursor = self.db.cursor()
        cursor.execute("INSERT INTO facts (fact) VALUES (?)", (fact,))
        self.db.commit()

    def get_long_term_facts(self) -> List[str]:
        cursor = self.db.cursor()
        cursor.execute("SELECT fact FROM facts ORDER BY timestamp DESC")
        return [r["fact"] for r in cursor.fetchall()]

    @staticmethod
    def _get_db_path():
        path = PLUGINS_DIR / "memory" / "storage.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def update_profile_static(updates: Dict[str, Any]):
        """Static method to update the agent profile from tools."""
        data_dir = PLUGINS_DIR / "memory"
        profile_path = data_dir / "config.json"
        
        current_data = {}
        if profile_path.exists():
            try:
                current_data = json.loads(profile_path.read_text(encoding="utf-8"))
            except: pass
        
        current_data.update(updates)
        data_dir.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(json.dumps(current_data, indent=4), encoding="utf-8")

    @staticmethod
    def add_fact_static(fact: str):
        """Static method to add a long-term fact from tools."""
        conn = sqlite3.connect(MemoryManager._get_db_path())
        cursor = conn.cursor()
        cursor.execute("INSERT INTO facts (fact) VALUES (?)", (fact,))
        conn.commit()
        conn.close()

    @staticmethod
    def clear_history_static():
        """Static method to clear chat history from tools."""
        conn = sqlite3.connect(MemoryManager._get_db_path())
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history")
        conn.commit()
        conn.close()

    async def healthcheck(self) -> tuple[bool, str]:
        try:
            self.db.execute("SELECT 1")
            return True, "Memory system operational."
        except Exception as e:
            return False, f"Memory DB Error: {e}"
