"""
Stackd AI Agent Stack — ACTIVE
Sea Breeze Maintenance — Francisco Da Silva
"""
import logging
import schedule
import time
import threading
import os
import uvicorn
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

from agents.ceo_agent import run
from tools.webhook import register_routes

app = FastAPI(title="Stackd AI — Sea Breeze Agents")
register_routes(app)


def run_scheduler():
    logger.info("🚀 Stackd AI Agent Stack starting...")
    run()
    schedule.every(5).minutes.do(run)
    logger.info("✅ Agents running — checking every 5 minutes")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🌐 Webhook server starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
