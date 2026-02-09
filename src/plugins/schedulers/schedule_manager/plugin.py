import sqlite3
from datetime import datetime
from src.core.interfaces import BaseScheduler
from src.core.paths import PLUGINS_DIR
from .config import ScheduleManagerConfig

class ScheduleManager(BaseScheduler[ScheduleManagerConfig]):
    """
    Central task manager.
    Monitors the database and executes reminders/tasks when the time comes.
    """
    name = "schedule_manager"
    config_class = ScheduleManagerConfig

    def __init__(self):
        super().__init__()
        self._init_db()

    def _init_db(self):
        cursor = self.db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT, -- 'reminder' or 'cron'
                description TEXT,
                schedule TEXT,   -- ISO timestamp for reminders or cron string
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.commit()

    @staticmethod
    def add_task(task_type: str, description: str, schedule: str):
        """Static method to add tasks to the central database from anywhere in the system."""
        db_path = PLUGINS_DIR / "schedule_manager" / "storage.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (task_type, description, schedule) VALUES (?, ?, ?)",
            (task_type, description, schedule)
        )
        conn.commit()
        conn.close()

    async def run_iteration(self, router):
        """Checks if there are tasks that need to be executed right now."""
        cursor = self.db.cursor()
        now = datetime.now().isoformat()

        cursor.execute(
            "SELECT id, description FROM tasks WHERE task_type = 'reminder' AND status = 'pending' AND schedule <= ?",
            (now,)
        )
        due_tasks = cursor.fetchall()

        for task in due_tasks:
            task_id, desc = task[0], task[1]

            await router.process_message(
                f"⏰ REMINDER: {desc}",
                source="schedule_manager"
            )

            cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))

        self.db.commit()

    async def healthcheck(self) -> tuple[bool, str]:
        try:
            self.db.execute("SELECT 1")
            return True, "Central Scheduler DB is healthy."
        except Exception as e:
            return False, f"DB Error: {e}"
