"""
APScheduler-based scheduler — runs the campaign on a configurable interval.
Reads POST_INTERVAL_HOURS fresh at start time so Settings changes take effect
on the next scheduler start.
"""
import os
import signal
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger
from .orchestrator import run_campaign


def _campaign_job():
    logger.info("Scheduled campaign starting...")
    results = run_campaign(use_ai=True)
    summary = results.get("_summary", {})
    if results.get("error"):
        logger.error(f"Campaign error: {results['error']}")
    else:
        logger.info(f"Campaign summary: posted={summary.get('success')} failed={summary.get('failed')}")


def start():
    hours = int(os.getenv("POST_INTERVAL_HOURS", "6"))
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        _campaign_job,
        trigger="interval",
        hours=hours,
        id="ebook_campaign",
        replace_existing=True,
    )

    def _shutdown(sig, frame):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    # SIGTERM not available on Windows — only register on Unix
    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    logger.info(f"Scheduler started — will post every {hours} hour(s).")
    logger.info("Running initial campaign now...")
    _campaign_job()
    scheduler.start()
