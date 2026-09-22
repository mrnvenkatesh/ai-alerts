"""
Scheduler & Main Entry Point for Daily GenAI News Aggregator.

Supports immediate execution (--now), dry-run testing (--dry-run), and APScheduler daily automation at 06:00 AM IST.
"""

import argparse
from datetime import datetime
import logging
import os
import sys
import time

from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("MainScheduler")

# Import internal modules safely
try:
    from src.fetcher import NewsFetcher
    from src.synthesizer import NewsSynthesizer
    from src.mailer import DigestMailer
except ImportError:
    from fetcher import NewsFetcher
    from synthesizer import NewsSynthesizer
    from mailer import DigestMailer


def run_pipeline(dry_run: bool = False, hours_lookback: int = 24, max_stories: int = 8) -> bool:
    """Executes the complete end-to-end ingestion, synthesis, and delivery pipeline."""
    tz_name = os.getenv("TIMEZONE", "Asia/Kolkata")
    local_tz = pytz.timezone(tz_name)
    now_local = datetime.now(local_tz)
    date_str = now_local.strftime("%B %d, %Y")

    logger.info(f"=== STARTING DAILY GENAI NEWS AGGREGATOR PIPELINE [{date_str}] ===")

    # Step 1: Ingestion & Deduplication
    fetcher = NewsFetcher(hours_lookback=hours_lookback)
    items = fetcher.fetch_all()
    logger.info(f"Pipeline step 1 complete: Ingested & deduplicated {len(items)} items.")

    # Step 2: LLM Synthesis & Filtering
    synthesizer = NewsSynthesizer(max_stories=max_stories)
    digest_content = synthesizer.synthesize(items, date_str)
    logger.info(f"Pipeline step 2 complete: Synthesized briefing with {len(digest_content.top_breakthroughs)} breakthroughs.")

    # Step 3: Formatting & Delivery
    mailer = DigestMailer()
    success = mailer.send_digest(digest_content, dry_run=dry_run)
    if success:
        logger.info(f"=== PIPELINE COMPLETED SUCCESSFULLY [{date_str}] ===")
    else:
        logger.warning(f"=== PIPELINE COMPLETED WITH WARNINGS/FALLBACKS [{date_str}] ===")

    return success


def start_scheduler():
    """Configures and runs APScheduler for daily execution at 06:00 AM IST."""
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    tz_name = os.getenv("TIMEZONE", "Asia/Kolkata")
    local_tz = pytz.timezone(tz_name)

    scheduler = BlockingScheduler(timezone=local_tz)

    # Schedule daily at 06:00 AM IST (00:30 UTC)
    cron_trigger = CronTrigger(hour=6, minute=0, timezone=local_tz)
    scheduler.add_job(
        run_pipeline,
        trigger=cron_trigger,
        kwargs={"dry_run": False, "hours_lookback": 24},
        id="daily_genai_briefing",
        name="Daily GenAI Briefing Job",
        replace_existing=True,
    )

    logger.info(f"APScheduler initialized. Target execution: Daily at 06:00 AM ({tz_name}).")
    logger.info("Scheduler running... Press Ctrl+C to exit.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


def main():
    parser = argparse.ArgumentParser(description="Daily GenAI News Aggregator & Email Digest")
    parser.add_argument("--now", action="store_true", help="Run pipeline immediately")
    parser.add_argument("--schedule", action="store_true", help="Start daily scheduled execution at 06:00 AM IST")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending SMTP email (saves HTML/text output locally)")
    parser.add_argument("--hours", type=int, default=24, help="Ingestion lookback window in hours (default: 24)")
    parser.add_argument("--max-stories", type=int, default=8, help="Maximum number of top stories in digest (default: 8)")

    args = parser.parse_args()

    if args.schedule:
        start_scheduler()
    elif args.now or args.dry_run:
        run_pipeline(dry_run=args.dry_run, hours_lookback=args.hours, max_stories=args.max_stories)
    else:
        # Default action: run --now with dry-run if no args specified
        logger.info("No explicit flag provided. Running immediate pipeline in dry-run mode...")
        run_pipeline(dry_run=True, hours_lookback=args.hours, max_stories=args.max_stories)


if __name__ == "__main__":
    main()
