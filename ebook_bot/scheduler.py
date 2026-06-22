"""
APScheduler-based scheduler — runs the campaign on a configurable interval.
"""
import signal
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger
from .config import POST_INTERVAL_HOURS
from .orchestrator import run_campaign


def _campaign_job():
    logger.info("Scheduled campaign starting...")
    results = run_campaign(use_ai=True)
    summary = results.get("_summary", {})
    logger.info(f"Campaign summary: {summary}")


def start():
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        _campaign_job,
        trigger="interval",
        hours=POST_INTERVAL_HOURS,
        id="ebook_campaign",
        replace_existing=True,
    )

    def _shutdown(sig, frame):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info(f"Scheduler started — will post every {POST_INTERVAL_HOURS} hour(s).")
    logger.info("Running initial campaign now...")
    _campaign_job()  # run immediately on start
    scheduler.start()
