"""Unit tests for periodic job orchestration."""

import asyncio
from datetime import timedelta

import pytest

from app.scheduler.periodic import PeriodicJob, PeriodicScheduler


async def test_scheduler_runs_job_immediately_and_repeats() -> None:
    called = asyncio.Event()
    calls = 0

    async def job() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            called.set()

    scheduler = PeriodicScheduler((PeriodicJob("test", timedelta(milliseconds=5), job),))
    scheduler.start()
    try:
        await asyncio.wait_for(called.wait(), timeout=0.2)
    finally:
        await scheduler.stop()
    assert calls >= 2


async def test_scheduler_isolates_job_failures() -> None:
    recovered = asyncio.Event()
    calls = 0

    async def flaky_job() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary failure")
        recovered.set()

    scheduler = PeriodicScheduler((PeriodicJob("flaky", timedelta(milliseconds=5), flaky_job),))
    scheduler.start()
    try:
        await asyncio.wait_for(recovered.wait(), timeout=0.2)
    finally:
        await scheduler.stop()
    assert calls >= 2


def test_job_interval_must_be_positive() -> None:
    async def job() -> None:
        return None

    with pytest.raises(ValueError, match="positive"):
        PeriodicJob("invalid", timedelta(0), job)
