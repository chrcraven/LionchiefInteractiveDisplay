"""Job scheduler for automated train control sequences."""
import asyncio
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from croniter import croniter
import uuid

from api.train_script import TrainScriptInterpreter, TrainScriptError

logger = logging.getLogger(__name__)

JOBS_FILE = "scheduled_jobs.json"


@dataclass
class ScheduledJob:
    """Represents a scheduled train control job."""
    id: str
    name: str
    description: str
    script: str
    cron_expression: str
    enabled: bool
    created_at: str
    last_run: Optional[str] = None
    last_result: Optional[str] = None
    run_count: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ScheduledJob':
        """Create from dictionary."""
        return cls(**data)


class JobScheduler:
    """Scheduler for running train control jobs on cron schedules."""

    def __init__(self, train_controller):
        """
        Initialize job scheduler.

        Args:
            train_controller: TrainController instance
        """
        self.train_controller = train_controller
        self.jobs: Dict[str, ScheduledJob] = {}
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.scheduler_task: Optional[asyncio.Task] = None
        self.is_running = False
        self._load_jobs()

    def _load_jobs(self):
        """Load jobs from file."""
        try:
            if os.path.exists(JOBS_FILE):
                with open(JOBS_FILE, 'r') as f:
                    data = json.load(f)
                    self.jobs = {
                        job_id: ScheduledJob.from_dict(job_data)
                        for job_id, job_data in data.items()
                    }
                logger.info(f"Loaded {len(self.jobs)} scheduled jobs")
        except Exception as e:
            logger.error(f"Error loading jobs: {e}")
            self.jobs = {}

    def _save_jobs(self) -> bool:
        """Save jobs to file."""
        try:
            data = {job_id: job.to_dict() for job_id, job in self.jobs.items()}
            with open(JOBS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving jobs: {e}")
            return False

    def create_job(
        self,
        name: str,
        description: str,
        script: str,
        cron_expression: str,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new scheduled job.

        Args:
            name: Job name
            description: Job description
            script: Train control script
            cron_expression: Cron expression for schedule
            enabled: Whether job is enabled

        Returns:
            Result dictionary with job info
        """
        # Validate cron expression
        if not self._validate_cron(cron_expression):
            return {
                "success": False,
                "error": "Invalid cron expression"
            }

        # Validate script
        try:
            interpreter = TrainScriptInterpreter(self.train_controller)
            interpreter.parse_script(script)
        except TrainScriptError as e:
            return {
                "success": False,
                "error": f"Script validation failed: {str(e)}"
            }

        # Create job
        job = ScheduledJob(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            script=script,
            cron_expression=cron_expression,
            enabled=enabled,
            created_at=datetime.now().isoformat(),
            last_run=None,
            last_result=None,
            run_count=0
        )

        self.jobs[job.id] = job
        self._save_jobs()

        logger.info(f"Created job '{name}' (ID: {job.id})")

        return {
            "success": True,
            "job": job.to_dict()
        }

    def update_job(
        self,
        job_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        script: Optional[str] = None,
        cron_expression: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update an existing job."""
        if job_id not in self.jobs:
            return {
                "success": False,
                "error": "Job not found"
            }

        job = self.jobs[job_id]

        # Validate cron if provided
        if cron_expression is not None:
            if not self._validate_cron(cron_expression):
                return {
                    "success": False,
                    "error": "Invalid cron expression"
                }
            job.cron_expression = cron_expression

        # Validate script if provided
        if script is not None:
            try:
                interpreter = TrainScriptInterpreter(self.train_controller)
                interpreter.parse_script(script)
                job.script = script
            except TrainScriptError as e:
                return {
                    "success": False,
                    "error": f"Script validation failed: {str(e)}"
                }

        if name is not None:
            job.name = name
        if description is not None:
            job.description = description
        if enabled is not None:
            job.enabled = enabled

        self._save_jobs()

        logger.info(f"Updated job '{job.name}' (ID: {job_id})")

        return {
            "success": True,
            "job": job.to_dict()
        }

    def delete_job(self, job_id: str) -> Dict[str, Any]:
        """Delete a job."""
        if job_id not in self.jobs:
            return {
                "success": False,
                "error": "Job not found"
            }

        # Stop if running
        if job_id in self.running_jobs:
            self.running_jobs[job_id].cancel()
            del self.running_jobs[job_id]

        job_name = self.jobs[job_id].name
        del self.jobs[job_id]
        self._save_jobs()

        logger.info(f"Deleted job '{job_name}' (ID: {job_id})")

        return {
            "success": True,
            "message": f"Job '{job_name}' deleted"
        }

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    def list_jobs(self) -> List[Dict]:
        """List all jobs."""
        return [job.to_dict() for job in self.jobs.values()]

    async def run_job_now(self, job_id: str) -> Dict[str, Any]:
        """Run a job immediately (outside of schedule)."""
        if job_id not in self.jobs:
            return {
                "success": False,
                "error": "Job not found"
            }

        if job_id in self.running_jobs:
            return {
                "success": False,
                "error": "Job is already running"
            }

        job = self.jobs[job_id]
        logger.info(f"Running job '{job.name}' manually")

        result = await self._execute_job(job)
        return result

    def _validate_cron(self, cron_expression: str) -> bool:
        """Validate a cron expression."""
        try:
            croniter(cron_expression)
            return True
        except Exception:
            return False

    async def start(self):
        """Start the job scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Job scheduler started")

    async def stop(self):
        """Stop the job scheduler."""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel scheduler task
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass

        # Cancel running jobs
        for task in self.running_jobs.values():
            task.cancel()

        self.running_jobs.clear()
        logger.info("Job scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("Scheduler loop started")

        try:
            while self.is_running:
                now = datetime.now()

                # Check each job
                for job_id, job in list(self.jobs.items()):
                    if not job.enabled:
                        continue

                    # Check if job should run
                    if self._should_run_job(job, now):
                        # Don't run if already running
                        if job_id not in self.running_jobs:
                            logger.info(f"Starting scheduled job '{job.name}'")
                            task = asyncio.create_task(self._execute_job(job))
                            self.running_jobs[job_id] = task

                # Clean up completed tasks
                completed = [
                    job_id for job_id, task in self.running_jobs.items()
                    if task.done()
                ]
                for job_id in completed:
                    del self.running_jobs[job_id]

                # Sleep for a bit before next check
                await asyncio.sleep(30)  # Check every 30 seconds

        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")

    def _should_run_job(self, job: ScheduledJob, now: datetime) -> bool:
        """Check if a job should run now."""
        try:
            cron = croniter(job.cron_expression, now)

            # Get previous scheduled time
            prev_time = cron.get_prev(datetime)

            # If last run is None or before previous scheduled time, should run
            if job.last_run is None:
                return True

            last_run_time = datetime.fromisoformat(job.last_run)

            # Should run if last run was before the previous scheduled time
            return last_run_time < prev_time

        except Exception as e:
            logger.error(f"Error checking job schedule: {e}")
            return False

    async def _execute_job(self, job: ScheduledJob) -> Dict[str, Any]:
        """Execute a job's script."""
        try:
            # Update job status
            job.last_run = datetime.now().isoformat()
            job.run_count += 1
            self._save_jobs()

            # Create interpreter and execute script
            interpreter = TrainScriptInterpreter(self.train_controller)
            result = await interpreter.execute_script(job.script)

            # Update job result
            if result.get("success"):
                job.last_result = "Success"
                logger.info(f"Job '{job.name}' completed successfully")
            else:
                job.last_result = f"Error: {result.get('error', 'Unknown error')}"
                logger.error(f"Job '{job.name}' failed: {result.get('error')}")

            self._save_jobs()

            return result

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            job.last_result = error_msg
            self._save_jobs()
            logger.error(f"Error executing job '{job.name}': {e}")
            return {
                "success": False,
                "error": error_msg
            }


# Global scheduler instance (initialized in main.py)
job_scheduler: Optional[JobScheduler] = None
