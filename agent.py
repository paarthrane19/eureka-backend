"""Standalone runner for the automated @eureka content agent.

The FastAPI app schedules this automatically via APScheduler (see
app/agent_scheduler.py) so nothing needs to run this manually in normal
operation. It's kept as a script for two cases:

  1. Manually posting one discovery right now, for testing:
         python agent.py --once

  2. Switching from the in-process scheduler to a Railway cron job: set up
     a Railway cron trigger to run `python agent.py --once` on whatever
     cadence you want, and set AGENT_ENABLED=false in the environment so
     the in-process scheduler doesn't also post.
"""

import argparse
import asyncio

from app.agent_core import post_next
from app.database import close_mongo_connection, connect_to_mongo


async def _run_once() -> None:
    await connect_to_mongo()
    try:
        await post_next()
    finally:
        await close_mongo_connection()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the @eureka content agent.")
    parser.add_argument(
        "--once", action="store_true", help="Post a single discovery and exit."
    )
    args = parser.parse_args()
    if not args.once:
        parser.error("pass --once (the FastAPI app handles ongoing scheduling)")
    asyncio.run(_run_once())


if __name__ == "__main__":
    main()
