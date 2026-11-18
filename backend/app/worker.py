import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import configure_logging, get_logger
from app.services.intelligence import IntelligenceModulesService
from app.services.scheduler_jobs import (
    run_gmail_sync_job,
    run_scheduled_cleanup_job,
    seed_default_rules_and_policies,
)

logger = get_logger("worker")


async def job_sync_inbox() -> None:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("http://backend:8000/api/v1/emails/sync")
            logger.info("worker_sync_job_delegated_to_backend", status_code=resp.status_code)
    except Exception as exc:
        logger.warning("worker_sync_delegation_failed", error=str(exc))


async def job_daily_cleanup() -> None:
    async with AsyncSessionLocal() as db:
        res = await run_scheduled_cleanup_job(db)
        logger.info("worker_cleanup_job_completed", **res)


async def job_weekly_digest() -> None:
    async with AsyncSessionLocal() as db:
        intel = IntelligenceModulesService()
        res = await intel.generate_and_archive_weekly_digest(db, send_telegram=True)
        logger.info("worker_weekly_digest_completed", processed_count=res["processed_count"])


async def main() -> None:
    configure_logging()
    settings = get_settings()

    async with AsyncSessionLocal() as db:
        await seed_default_rules_and_policies(db)

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        job_sync_inbox,
        IntervalTrigger(minutes=settings.SYNC_INTERVAL_MINUTES),
        id="gmail_sync_job",
        replace_existing=True,
    )
    scheduler.add_job(
        job_daily_cleanup,
        CronTrigger(hour=settings.CLEANUP_CRON_HOUR, minute=0),
        id="daily_safe_cleanup_job",
        replace_existing=True,
    )
    scheduler.add_job(
        job_weekly_digest,
        CronTrigger(day_of_week=settings.DIGEST_DAY_OF_WEEK, hour=settings.DIGEST_HOUR, minute=0),
        id="weekly_knowledge_digest_job",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "emailos_worker_started",
        sync_interval_minutes=settings.SYNC_INTERVAL_MINUTES,
        cleanup_cron_hour=settings.CLEANUP_CRON_HOUR,
    )

    stop_event = asyncio.Event()
    await stop_event.wait()


if __name__ == "__main__":
    asyncio.run(main())
