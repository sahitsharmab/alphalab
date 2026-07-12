"""Small async periodic scheduler with no business logic."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta

import structlog

logger = structlog.get_logger(__name__)

JobCallback = Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class PeriodicJob:
    """A named async callback and its execution interval."""

    name: str
    interval: timedelta
    callback: JobCallback

    def __post_init__(self) -> None:
        if self.interval.total_seconds() <= 0:
            raise ValueError("job interval must be positive")


class PeriodicScheduler:
    """Run independent jobs immediately and then at fixed intervals."""

    def __init__(self, jobs: tuple[PeriodicJob, ...]) -> None:
        self._jobs = jobs
        self._tasks: list[asyncio.Task[None]] = []

    def start(self) -> None:
        """Start all job loops; calling twice is an error."""
        if self._tasks:
            raise RuntimeError("scheduler already started")
        self._tasks = [asyncio.create_task(self._run(job)) for job in self._jobs]
        logger.info("scheduler_started", jobs=[job.name for job in self._jobs])

    async def stop(self) -> None:
        """Cancel jobs and wait for their cleanup."""
        tasks, self._tasks = self._tasks, []
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("scheduler_stopped")

    async def _run(self, job: PeriodicJob) -> None:
        while True:
            started = asyncio.get_running_loop().time()
            try:
                await job.callback()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("scheduled_job_failed", job=job.name)
            else:
                elapsed = asyncio.get_running_loop().time() - started
                logger.info("scheduled_job_completed", job=job.name, latency_seconds=elapsed)
            await asyncio.sleep(job.interval.total_seconds())
