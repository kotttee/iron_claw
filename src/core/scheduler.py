import asyncio
import datetime
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger, CronTriggerError
from rich.console import Console

if TYPE_CHECKING:
    from src.core.router import MessageRouter

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DATA_DIR.resolve()}/scheduler.sqlite"

def job_callback(job_id: str, router: "MessageRouter", context: Dict[str, Any], message: str):
    """Top-level function for APScheduler to call, which then calls into the router."""
    console = Console()
    console.print(f"[bold yellow]Scheduler:[/bold yellow] Triggering job '{job_id}'.")
    asyncio.create_task(router.handle_scheduled_event(context, message))

class SchedulerManager:
    """Manages all scheduling operations with a persistent backend."""
    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": SQLAlchemyJobStore(url=DATABASE_URL)},
            job_defaults={"misfire_grace_time": 60 * 15},  # 15 minutes
        )
        self.router: "MessageRouter" | None = None
        self.console = Console()

    def start(self, router: "MessageRouter"):
        """Starts the scheduler and links it to the message router."""
        self.router = router
        if not self.scheduler.running:
            self.scheduler.start()
            self.console.print("[green]✔ Scheduler started with persistent backend.[/green]")

    def stop(self):
        """Stops the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown()

    def add_date_job(self, run_date: datetime.datetime, message: str, context: Dict[str, Any]) -> str:
        """Adds a one-time job to the scheduler for a specific date."""
        if not self.router:
            return "Error: Scheduler is not initialized with a router."
        try:
            job_id = f"date_{context.get('user_id', 'anon')}_{int(run_date.timestamp())}"
            job = self.scheduler.add_job(
                job_callback, "date", run_date=run_date, id=job_id,
                args=[None, self.router, context, message]
            )
            job.modify(args=[job.id, self.router, context, message])
            return f"OK. One-time job set for {run_date.isoformat()}. Job ID: {job.id}"
        except Exception as e:
            return f"Error setting date-based job: {e}"

    def add_cron_job(self, cron_expression: str, message: str, context: Dict[str, Any]) -> str:
        """Adds a recurring job based on a Cron expression."""
        if not self.router:
            return "Error: Scheduler is not initialized with a router."
        try:
            # Validate the cron expression before adding the job
            trigger = CronTrigger.from_crontab(cron_expression)
            job_id = f"cron_{context.get('user_id', 'anon')}_{hash(cron_expression) & 0xffffff}"
            job = self.scheduler.add_job(
                job_callback, trigger, id=job_id,
                args=[None, self.router, context, message]
            )
            job.modify(args=[job.id, self.router, context, message])
            return f"OK. Recurring job set with schedule '{cron_expression}'. Job ID: {job.id}"
        except CronTriggerError as e:
            return f"Error: Invalid Cron expression '{cron_expression}'. {e}"
        except Exception as e:
            return f"Error setting cron job: {e}"

    def list_jobs(self) -> str:
        """Returns a formatted string of all scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        if not jobs:
            return "No scheduled jobs."
        job_list = ["Scheduled Jobs:"]
        for job in jobs:
            job_list.append(f"- ID: {job.id}, Trigger: {job.trigger}, Next Run: {job.next_run_time}")
        return "\n".join(job_list)

    def delete_job(self, job_id: str) -> str:
        """Deletes a job by its ID."""
        try:
            self.scheduler.remove_job(job_id)
            return f"Successfully deleted job '{job_id}'."
        except Exception as e:
            return f"Error deleting job '{job_id}': {e}"
