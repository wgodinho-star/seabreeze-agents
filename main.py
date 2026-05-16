"""
EMERGENCY PAUSE — Twilio runaway SMS loop detected
Scheduling Agent was sending SMS every 5 minutes to test contact
All agents stopped until issue is fixed
"""
import logging, time
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.error("🚨 EMERGENCY PAUSE — Agents stopped due to runaway SMS loop")
logger.error("   Scheduling Agent was sending SMS every 5 min to +61433332514")
logger.error("   Fix: Remove test contact from scheduling queue")
logger.error("   Then set AGENTS_PAUSED=false to resume")
while True:
    logger.info("⏸️  Paused — waiting for fix...")
    time.sleep(3600)
