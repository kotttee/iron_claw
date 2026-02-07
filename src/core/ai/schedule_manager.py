import asyncio
import datetime
import json
from typing import Any, Dict, TYPE_CHECKING

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console

if TYPE_CHECKING:
    from src.core.ai.router import Router

from src.core.paths import DATA_ROOT
DATABASE_URL = f"sqlite:///{DATA_ROOT.resolve()}/scheduler.sqlite"

def execute_scheduled_task(router: "Router", task_info_json: str):
    """
    Top-level function for APScheduler to execute a scheduled task.
    This function deserializes the task info and routes it appropriately.
    """
    console = Console()
    try:
        task_info = json.loads(task_info_json)
        task_type = task_info.get("type", "generic")
        
        console.print(f"[bold yellow]Scheduler:[/bold yellow] Triggering task of type '{task_type}'")

        if task_type == "reminder":
            # Reminders have specific context and are handled by a dedicated async method
            asyncio.run(router.handle_reminder_event(task_info))
        else:
            # Generic tasks are handled by a synchronous method
            description = task_info.get("description", "No description provided.")
            router.handle_scheduled_event(description)

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

    def _add_job(self, task_info: Dict[str, Any], trigger_type: str, **trigger_args) -> str:
        if not self.router:
            return "Error: Scheduler is not initialized with a router."

        task_type = task_info.get("type", "generic")
        job_id_prefix = f"{task_type}_{int(datetime.datetime.now().timestamp())}"
        job_id = f"{job_id_prefix}_{hash(json.dumps(task_info)) & 0xffffff}"

        task_info_json = json.dumps(task_info)

        self.scheduler.add_job(
            execute_scheduled_task, trigger_type, id=job_id, args=[self.router, task_info_json], **trigger_args
        )
        return f"OK. Task scheduled. Job ID: {job_id}"

    def add_reminder(self, run_date: datetime.datetime, message: str) -> str:
        """Adds a one-time reminder job."""
        task_info = {"type": "reminder", "message": message}
        return self._add_job(task_info, "date", run_date=run_date)

    def add_date_task(self, run_date: datetime.datetime, task_description: str) -> str:
        """Adds a one-time generic task for a specific date."""
        task_info = {"type": "generic", "description": task_description}
        return self._add_job(task_info, "date", run_date=run_date)

    def add_cron_task(self, cron_expression: str, task_description: str) -> str:
        """Adds a recurring generic task."""
        try:
            trigger = CronTrigger.from_crontab(cron_expression)
            task_info = {"type": "generic", "description": task_description}
            return self._add_job(task_info, "cron", trigger=trigger)
        except ValueError as e:
            return f"Error: Invalid Cron expression '{cron_expression}'. Details: {e}"

    def list_jobs(self) -> str:
        """Lists all scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        if not jobs:
            return "No scheduled jobs."
        job_list = ["Scheduled Jobs:"]
        for job in jobs:
            try:
                task_info = json.loads(job.args[1])
                task_type = task_info.get("type", "generic")
                description = task_info.get("description") or task_info.get("message", "N/A")
            except (json.JSONDecodeError, IndexError):
                task_type = "unknown"
                description = f"Legacy or malformed task: {job.args[1] if len(job.args) > 1 else 'N/A'}"

            job_list.append(f"- ID: {job.id}, Type: {task_type.capitalize()}, Details: '{description}', Next Run: {job.next_run_time}")
        return "\n".join(job_list)

    def delete_job(self, job_id: str) -> str:
        """Deletes a job by its ID."""
        try:
            self.scheduler.remove_job(job_id)
            return f"Successfully deleted job '{job_id}'."
        except Exception as e:
            return f"Error deleting job '{job_id}': {e}"
