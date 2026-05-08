from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from .config import EnvSettings, RuntimeConfig, TagRule
from .digest import parse_digest_date, run_daily_digest

logger = logging.getLogger(__name__)


def build_scheduler(env: EnvSettings, runtime: RuntimeConfig, tags: list[TagRule]) -> BlockingScheduler:
    timezone = runtime.schedule.timezone or env.digest_timezone
    scheduler = BlockingScheduler(timezone=timezone)

    def job() -> None:
        today = parse_digest_date("today", timezone=timezone)
        logger.info("Starting scheduled digest for %s", today.isoformat())
        run_daily_digest(target_date=today, env=env, runtime=runtime, tags=tags)

    scheduler.add_job(
        job,
        trigger="cron",
        hour=runtime.schedule.hour,
        minute=runtime.schedule.minute,
        timezone=ZoneInfo(timezone),
        max_instances=1,
        id="daily_xhs_digest",
        replace_existing=True,
    )
    logger.info(
        "Scheduled daily digest at %02d:%02d %s",
        runtime.schedule.hour,
        runtime.schedule.minute,
        timezone,
    )
    return scheduler


def run_scheduler(env: EnvSettings, runtime: RuntimeConfig, tags: list[TagRule]) -> None:
    scheduler = build_scheduler(env, runtime, tags)
    logger.info("Scheduler started at %s", datetime.now().isoformat())
    scheduler.start()

