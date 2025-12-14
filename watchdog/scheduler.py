"""APScheduler configuration for background pipeline jobs."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from watchdog.config import get_settings


def create_scheduler() -> BackgroundScheduler:
    """Create and configure the background scheduler."""
    scheduler = BackgroundScheduler()
    
    # Run discovery every 2 hours
    scheduler.add_job(
        run_discover,
        trigger=IntervalTrigger(hours=2),
        id="discover",
        name="Discover new documents",
        replace_existing=True,
    )
    
    # Run fetch every hour
    scheduler.add_job(
        run_fetch,
        trigger=IntervalTrigger(hours=1),
        id="fetch",
        name="Fetch pending files",
        replace_existing=True,
    )
    
    # Run extraction every 30 minutes
    scheduler.add_job(
        run_extract,
        trigger=IntervalTrigger(minutes=30),
        id="extract",
        name="Extract text from PDFs",
        replace_existing=True,
    )
    
    # Run triage and case building twice daily
    scheduler.add_job(
        run_triage,
        trigger=CronTrigger(hour="6,18"),
        id="triage",
        name="Triage documents",
        replace_existing=True,
    )
    
    scheduler.add_job(
        run_case_builder,
        trigger=CronTrigger(hour="7,19"),
        id="case_builder",
        name="Build cases",
        replace_existing=True,
    )
    
    return scheduler


def run_discover():
    """Run discovery job."""
    try:
        from watchdog.pipeline import discover
        discover.run()
    except Exception as e:
        print(f"Discover job failed: {e}")


def run_fetch():
    """Run fetch job."""
    try:
        from watchdog.pipeline import fetch
        fetch.run()
    except Exception as e:
        print(f"Fetch job failed: {e}")


def run_extract():
    """Run extraction job."""
    try:
        from watchdog.pipeline import extract
        extract.run()
    except Exception as e:
        print(f"Extract job failed: {e}")


def run_triage():
    """Run triage job."""
    try:
        from watchdog.pipeline import triage
        triage.run()
    except Exception as e:
        print(f"Triage job failed: {e}")


def run_case_builder():
    """Run case builder job."""
    try:
        from watchdog.pipeline import case_builder
        case_builder.run()
    except Exception as e:
        print(f"Case builder job failed: {e}")


# Global scheduler instance
_scheduler = None


def get_scheduler() -> BackgroundScheduler:
    """Get or create the global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = create_scheduler()
    return _scheduler


def start_scheduler():
    """Start the background scheduler."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        print("✓ Background scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        print("✓ Background scheduler stopped")
