"""
Stackd AI — Sea Breeze Maintenance Agent Stack
All systems active. Scheduling bug fixed. Email templates loaded.
"""
import logging
import schedule
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

from agents.ceo_agent import run

logger.info("🚀 Stackd AI — Sea Breeze agents starting...")
run()

schedule.every(5).minutes.do(run)
logger.info("✅ All agents active — running every 5 minutes")

while True:
    schedule.run_pending()
    time.sleep(60)
