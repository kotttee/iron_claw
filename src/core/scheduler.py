import asyncio
import datetime
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console

if TYPE_CHECKING:
    from src.core.router import MessageRouter

DATA_DIR = Path("data")
DATABASE_URL = f"sqlite:///{DATA_DIR.resolve()}/scheduler.sqlite"

def job_callback(router: "MessageRouter", context: Dict[str, Any], message: str):
    """
    Top-level function for APScheduler. It calls back into the router's event handler.
    The job_id is now part of the context if needed, but not a direct argument.
    """
    console = Console()
    console.print(f"[bold yellow]Scheduler:[/bold yellow] Triggering job for target '{context.get('plugin_id')}'.")
    asyncio.create_task(router.handle_scheduled_event(context, message))

class SchedulerManager:
    """Manages all scheduling operations with a persistent backend."""
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": SQLAlchemyJobStore(url=DATABASE_URL)},
            job_defaults={"misfire_grace_time": 60 * 15},
        )
        self.router: "MessageRouter" | None = None
        self.console = Console()

    def start(self, router: "MessageRouter"):
        self.router = router
        if not self.scheduler.running:
            self.scheduler.start()
            self.console.print("[green]✔ Scheduler started with persistent backend.[/green]")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()

    def add_date_job(self, run_date: datetime.datetime, message: str, context: Dict[str, Any]) -> str:
        """Adds a one-time job. The context must contain routing information."""
        if not self.router: return "Error: Scheduler is not initialized."
        try:
            job_id = f"date_{context.get('user_contact_id', 'anon')}_{int(run_date.timestamp())}"
            self.scheduler.add_job(
                job_callback, "date", run_date=run_date, id=job_id,
                args=[self.router, context, message]
            )
            return f"OK. One-time job set for {run_date.isoformat()}. Job ID: {job_id}"
        except Exception as e:
            return f"Error setting date-based job: {e}"

    def add_cron_job(self, cron_expression: str, message: str, context: Dict[str, Any]) -> str:
        """Adds a recurring job. The context must contain routing information."""
        if not self.router: return "Error: Scheduler is not initialized."
        try:
            trigger = CronTrigger.from_crontab(cron_expression)
            job_id = f"cron_{context.get('user_contact_id', 'anon')}_{hash(cron_expression) & 0xffffff}"
            self.scheduler.add_job(
                job_callback, trigger, id=job_id,
                args=[self.router, context, message]
            )
            return f"OK. Recurring job set with schedule '{cron_expression}'. Job ID: {job_id}"
        except ValueError as e:
            return f"Error: Invalid Cron expression '{cron_expression}'. Details: {e}"
        except Exception as e:
            return f"Error setting cron job: {e}"

    def list_jobs(self) -> str:
        jobs = self.scheduler.get_jobs()
        if not jobs: return "No scheduled jobs."
        job_list = ["Scheduled Jobs:"]
        for job in jobs:
            job_list.append(f"- ID: {job.id}, Trigger: {job.trigger}, Next Run: {job.next_run_time}")
        return "\n".join(job_list)

    def delete_job(self, job_id: str) -> str:
        try:
            self.scheduler.remove_job(job_id)
            return f"Successfully deleted job '{job_id}'."
        except Exception as e:
            return f"Error deleting job '{job_id}': {e}"
