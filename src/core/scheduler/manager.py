import asyncio
import sqlite3
import json
import aiocron
from datetime import datetime
from typing import List, Dict, Optional, Any
from src.core.paths import DATA_ROOT

class CoreScheduler:
    """
    Центральный системный планировщик.
    Использует aiocron для регулярных задач и внутренний цикл для напоминаний.
    """
    def __init__(self, router):
        self.router = router
        self.db_path = DATA_ROOT / "core" / "scheduler.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.cron_jobs = {}
        self._stop_event = asyncio.Event()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT, -- 'cron' или 'reminder'
                description TEXT,
                schedule TEXT,   -- cron-выражение или ISO timestamp
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    async def start(self):
        """Запуск планировщика и восстановление задач из базы."""
        # Восстанавливаем cron-задачи
        tasks = self.list_tasks()
        for task in tasks:
            if task['task_type'] == 'cron':
                self._register_cron(task['id'], task['schedule'], task['description'])
        
        # Запускаем цикл проверки одноразовых напоминаний
        asyncio.create_task(self._reminder_loop())

    def _register_cron(self, task_id: int, spec: str, description: str):
        """Регистрация задачи в aiocron."""
        async def cron_wrapper():
            await self.router.process_message(
                f"⏰ Scheduled Task: {description}", 
                source="scheduler"
            )
        
        job = aiocron.crontab(spec, func=cron_wrapper, start=True)
        self.cron_jobs[task_id] = job

    async def add_task(self, task_type: str, description: str, schedule: str) -> int:
        """Добавление новой задачи в базу и активация."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (task_type, description, schedule) VALUES (?, ?, ?)",
            (task_type, description, schedule)
        )
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        if task_type == 'cron':
            self._register_cron(task_id, schedule, description)
        
        return task_id

    def delete_task(self, task_id: int) -> bool:
        """Удаление задачи из базы и остановка cron-джобы."""
        if task_id in self.cron_jobs:
            self.cron_jobs[task_id].stop()
            del self.cron_jobs[task_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def list_tasks(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE status = 'pending'")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    async def _reminder_loop(self):
        """Цикл проверки одноразовых напоминаний."""
        while not self._stop_event.is_set():
            now = datetime.now().isoformat()
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tasks WHERE task_type = 'reminder' AND status = 'pending' AND schedule <= ?",
                (now,)
            )
            due_tasks = cursor.fetchall()
            
            for task in due_tasks:
                await self.router.process_message(f"🔔 Reminder: {task['description']}", source="scheduler")
                cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task['id'],))
            
            conn.commit()
            conn.close()
            await asyncio.sleep(10) # Проверка каждые 10 секунд