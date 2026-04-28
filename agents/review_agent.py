"""
Review Agent — sends Google review requests to clients
after jobs are marked as Won/Completed in the pipeline.
"""
import logging
from tools import ghl, claude_ai

logger = logging.getLogger(__name__)

GOOGLE_REVIEW_LINK = "https://g.page/r/SEABREEZE_REVIEW_LINK/review"  # Replace with real link


def run():
    """Check for recently won opportunities and send review requests."""
    logger.info("⭐ Review Agent: Checking for completed jobs...")

    opportunities = ghl.get_opportunities()
    won_jobs = [
        o for o in opportunities
        if o.get("status") == "won"
        and "review-requested" not in (o.get("contact", {}).get("tags") or [])
    ]

    if not won_jobs:
        logger.info("✅ No new completed jobs to review.")
        return

    for job in won_jobs:
        contact_id = job.get("contact", {}).get("id")
        contact_name = job.get("contact", {}).get("name", "there")
        job_title = job.get("name", "your recent service")

        if not contact_id:
            continue

        try:
            # Generate personalised review request
            sms = claude_ai.generate_review_request(contact_name, job_title)
            sms = sms.replace("[GOOGLE_LINK]", GOOGLE_REVIEW_LINK)

            # Send SMS
            ghl.send_sms(contact_id, sms)

            # Add note
            ghl.add_note(contact_id, f"Review Agent: Review request SMS sent.\nMessage: {sms}")

            # Tag contact so we don't double-send
            existing_tags = job.get("contact", {}).get("tags", [])
            ghl.update_contact_tags(contact_id, existing_tags + ["review-requested"])

            logger.info(f"⭐ Review request sent to {contact_name}")

        except Exception as e:
            logger.error(f"❌ Error sending review request: {e}")

    logger.info(f"🏁 Review Agent: Processed {len(won_jobs)} completed jobs.")
