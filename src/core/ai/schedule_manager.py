import asyncio
import datetime
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console

if TYPE_CHECKING:
    from src.core.ai.router import Router

from src.core.paths import DATA_ROOT
DATABASE_URL = f"sqlite:///{DATA_ROOT.resolve()}/scheduler.sqlite"

def execute_scheduled_task(router: "Router", task_description: str):
    """
    Top-level function for APScheduler to execute a scheduled task.
    This function calls the router's method to handle the event.
    """
    console = Console()
    console.print(f"[bold yellow]Scheduler:[/bold yellow] Triggering task: '{task_description}'")
    # The router's handle_scheduled_event is now synchronous and handles its own async operations if needed
    try:
        router.handle_scheduled_event(task_description)
    except Exception as e:
        console.print(f"[bold red]Error executing scheduled task:[/bold red] {e}")

class SchedulerManager:
    """Manages all scheduling operations with a persistent backend."""
    def __init__(self):
        DATA_ROOT.mkdir(exist_ok=True)
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": SQLAlchemyJobStore(url=DATABASE_URL)},
            job_defaults={"misfire_grace_time": 60 * 15},
        )
        self.router: Any = None
        self.console = Console()

    def start(self, router: "Router"):
        """Starts the scheduler and stores a reference to the router."""
        self.router = router
        if not self.scheduler.running:
            self.scheduler.start()
            self.console.print("[green]✔ Scheduler started with persistent backend.[/green]")

    def stop(self):
        """Stops the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()

    def add_date_job(self, run_date: datetime.datetime, task_description: str) -> str:
        """Adds a one-time job."""
        if not self.router:
            return "Error: Scheduler is not initialized with a router."
        try:
            job_id = f"date_{int(run_date.timestamp())}"
            self.scheduler.add_job(
                execute_scheduled_task, "date", run_date=run_date, id=job_id,
                args=[self.router, task_description]
            )
            return f"OK. One-time job set for {run_date.isoformat()}. Job ID: {job_id}"
        except Exception as e:
            return f"Error setting date-based job: {e}"

    def add_cron_job(self, cron_expression: str, task_description: str) -> str:
        """Adds a recurring job."""
        if not self.router:
            return "Error: Scheduler is not initialized with a router."
        try:
            trigger = CronTrigger.from_crontab(cron_expression)
            job_id = f"cron_{hash(cron_expression) & 0xffffff}"
            self.scheduler.add_job(
                execute_scheduled_task, trigger, id=job_id,
                args=[self.router, task_description]
            )
            return f"OK. Recurring job set with schedule '{cron_expression}'. Job ID: {job_id}"
        except ValueError as e:
            return f"Error: Invalid Cron expression '{cron_expression}'. Details: {e}"
        except Exception as e:
            return f"Error setting cron job: {e}"

    def list_jobs(self) -> str:
        """Lists all scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        if not jobs:
            return "No scheduled jobs."
        job_list = ["Scheduled Jobs:"]
        for job in jobs:
            job_list.append(f"- ID: {job.id}, Task: '{job.args[1]}', Trigger: {job.trigger}, Next Run: {job.next_run_time}")
        return "\n".join(job_list)

    def delete_job(self, job_id: str) -> str:
        """Deletes a job by its ID."""
        try:
            self.scheduler.remove_job(job_id)
            return f"Successfully deleted job '{job_id}'."
        except Exception as e:
            return f"Error deleting job '{job_id}': {e}"
