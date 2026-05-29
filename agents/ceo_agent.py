"""
CEO Agent — the orchestrator brain.
Decides which agents to run and in what order.
Runs on every scheduler tick.
"""
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

SYDNEY_TZ = pytz.timezone("Australia/Sydney")


def run():
    """
    CEO Agent decision loop.
    Orchestrates all sub-agents based on time and conditions.
    """
    now = datetime.now(SYDNEY_TZ)
    hour = now.hour
    weekday = now.weekday()  # 0=Monday

    logger.info(f"🧠 CEO Agent: Tick at {now.strftime('%A %d %B %Y %H:%M')} Sydney time")

    # ── Always run: Lead Agent (every 5 min) ──────────────
    try:
        from agents.lead_agent import run as lead_run
        lead_run()
    except Exception as e:
        logger.error(f"❌ Lead Agent failed: {e}")

    # ── Briefing Agent (7am + 5pm daily) ────────────────────
    try:
        from agents.briefing_agent import run as briefing_run
        briefing_run()
    except Exception as e:
        logger.error(f"❌ Briefing Agent failed: {e}")

    # ── Social Agent (Monday mornings) ──────────────────────
    try:
        from agents.social_agent import run as social_run
        social_run()
    except Exception as e:
        logger.error(f"❌ Social Agent failed: {e}")

    # ── Follow-up Agent (weekday mornings) ───────────────────
    try:
        from agents.followup_agent import run as followup_run
        followup_run()
    except Exception as e:
        logger.error(f"❌ Follow-up Agent failed: {e}")

    # ── Outreach Agent (weekday mornings) ────────────────────
    try:
        from agents.outreach_agent import run as outreach_run
        outreach_run()
    except Exception as e:
        logger.error(f"❌ Outreach Agent failed: {e}")

    # ── Always run: Review Agent (every tick) ─────────────
    try:
        from agents.review_agent import run as review_run
        review_run()
    except Exception as e:
        logger.error(f"❌ Review Agent failed: {e}")

    # ── Health Agent (every hour) ────────────────────────────
    try:
        from agents.health_agent import run as health_run
        health_run()
    except Exception as e:
        logger.error(f"❌ Health Agent failed: {e}")

    # ── Always run: Scheduling Agent (every tick) ──────────────
    try:
        from agents.scheduling_agent import run as scheduling_run
        scheduling_run()
    except Exception as e:
        logger.error(f"❌ Scheduling Agent failed: {e}")

    # ── Monday 8am: Weekly Report ─────────────────────────
    if weekday == 0 and 8 <= hour < 9:
        logger.info("📊 CEO Agent: Triggering weekly report...")
        try:
            from agents.report_agent import run as report_run
            report_run()
        except Exception as e:
            logger.error(f"❌ Report Agent failed: {e}")

    logger.info("✅ CEO Agent: Tick complete.\n")
