"""
Seabreeze AI Agent Stack — Main Entry Point
Runs on Railway.app | Impeller Trust × Sea Breeze Maintenance
"""
import os
import logging
import time
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

INTERVAL_MINUTES = int(os.getenv("LEAD_CHECK_INTERVAL_MINUTES", 5))


def main():
    logger.info("🚀 Seabreeze AI Agent Stack starting...")
    logger.info(f"📍 Client: {os.getenv('CLIENT_NAME')}")
    logger.info(f"📍 Location ID: {os.getenv('GHL_SEABREEZE_LOCATION_ID')}")
    logger.info(f"⏱️  Check interval: every {INTERVAL_MINUTES} minutes")
    logger.info("─" * 50)

    from agents.ceo_agent import run as ceo_run

    while True:
        try:
            ceo_run()
        except Exception as e:
            logger.error(f"❌ Fatal error in CEO Agent: {e}")

        logger.info(f"😴 Sleeping {INTERVAL_MINUTES} minutes...\n")
        time.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
