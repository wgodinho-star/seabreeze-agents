"""
Enviromentor Agent Stack — ACTIVE
Sea Breeze Maintenance — Francisco Da Silva
"""
import logging
import schedule
import time
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

from agents.ceo_agent import run

# Run immediately on startup
logger.info("🚀 Enviromentor Agent Stack starting...")
run()

# Schedule every 5 minutes
schedule.every(5).minutes.do(run)

logger.info("✅ Agents running — checking every 5 minutes")

while True:
    schedule.run_pending()
    time.sleep(60)
