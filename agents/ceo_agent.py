"""
CEO Agent — the orchestrator brain.
Decides which agents to run and in what order.
Runs on every scheduler tick.
"""
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

PERTH_TZ = pytz.timezone("Australia/Perth")


def run():
    """
    CEO Agent decision loop.
    Orchestrates all sub-agents based on time and conditions.
    """
    now = datetime.now(PERTH_TZ)
    hour = now.hour
    weekday = now.weekday()  # 0=Monday

    logger.info(f"🧠 CEO Agent: Tick at {now.strftime('%A %d %B %Y %H:%M')} Perth time")

    # ── Always run: Lead Agent (every 5 min) ──────────────
    try:
        from agents.lead_agent import run as lead_run
        lead_run()
    except Exception as e:
        logger.error(f"❌ Lead Agent failed: {e}")

    # ── Always run: Review Agent (every tick) ─────────────
    try:
        from agents.review_agent import run as review_run
        review_run()
    except Exception as e:
        logger.error(f"❌ Review Agent failed: {e}")

    # ── Monday 8am: Weekly Report ─────────────────────────
    if weekday == 0 and 8 <= hour < 9:
        logger.info("📊 CEO Agent: Triggering weekly report...")
        try:
            from agents.report_agent import run as report_run
            report_run()
        except Exception as e:
            logger.error(f"❌ Report Agent failed: {e}")

    logger.info("✅ CEO Agent: Tick complete.\n")
