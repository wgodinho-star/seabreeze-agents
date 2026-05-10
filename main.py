"""
Enviromentor Agent Stack — PAUSED
Reason: Email sending not configured, domain not connected
Resume when: GHL email services configured + domain connected
"""
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("⏸️  Agent stack paused — awaiting email + domain setup")
logger.info("   Resume by updating AGENTS_PAUSED=false in Railway env vars")

import os
import time

PAUSED = os.getenv("AGENTS_PAUSED", "true").lower() == "true"

if PAUSED:
    logger.info("⏸️  Agents paused. Nothing will run until AGENTS_PAUSED=false")
    while True:
        time.sleep(3600)
        logger.info("⏸️  Still paused...")
else:
    # Normal operation
    from agents.ceo_agent import run
    import schedule
    schedule.every(5).minutes.do(run)
    while True:
        schedule.run_pending()
        time.sleep(60)
