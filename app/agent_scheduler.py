"""In-process scheduler for the automated @eureka content agent.

Chosen over a Railway cron job for simplicity: this is a single-service
deployment (one Railway service running the FastAPI app), so scheduling
inside the app's own event loop avoids standing up a second cron-triggered
service and duplicating DB connection setup. `agent.py` still exists as a
standalone script that does the same posting, so switching to an external
cron trigger later is a one-line change (call `python agent.py --once`
instead of relying on this scheduler).

Each day, `agent_posts_per_day` random times between "now" and the end of
the day are chosen and each is scheduled as a one-off job, so posts land
at natural, irregular intervals rather than all at once. A daily job at
00:05 re-runs the same random scheduling for the new day.
"""

import random
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from app.agent_core import post_next
from app.config import get_settings

_scheduler: AsyncIOScheduler | None = None


def _schedule_todays_posts(scheduler: AsyncIOScheduler) -> None:
    settings = get_settings()
    now = datetime.now()
    end_of_day = now.replace(hour=23, minute=55, second=0, microsecond=0)
    window_seconds = (end_of_day - now).total_seconds()
    if window_seconds < 60:
        return  # too close to midnight to fit any more posts today

    count = settings.agent_posts_per_day
    offsets = sorted(random.uniform(0, window_seconds) for _ in range(count))
    for i, offset in enumerate(offsets):
        run_date = now + timedelta(seconds=offset)
        scheduler.add_job(
            post_next,
            trigger=DateTrigger(run_date=run_date),
            id=f"agent-post-{run_date.date()}-{i}",
            replace_existing=True,
            misfire_grace_time=3600,
        )


def start_agent_scheduler() -> None:
    global _scheduler
    settings = get_settings()
    if not settings.agent_enabled or _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler()
    _schedule_todays_posts(_scheduler)
    _scheduler.add_job(
        _schedule_todays_posts,
        trigger="cron",
        hour=0,
        minute=5,
        args=[_scheduler],
        id="agent-daily-scheduler",
        replace_existing=True,
    )
    _scheduler.start()
    print(f"[agent] scheduler started, {settings.agent_posts_per_day} posts/day target")


def stop_agent_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
