"""
Lead Agent — monitors new inbound leads, qualifies them,
sends instant SMS reply, and moves them into the pipeline.
"""
import logging
from tools import ghl, claude_ai

logger = logging.getLogger(__name__)


def run():
    """Main lead agent loop — called every 5 minutes by scheduler."""
    logger.info("🔍 Lead Agent: Checking for new leads...")

    contacts = ghl.get_contacts(limit=50)
    new_leads = [
        c for c in contacts
        if "new-lead" in c.get("tags", [])
        and "lead-processed" not in c.get("tags", [])
        and "(example)" not in c.get("firstName", "").lower()
    ]

    if not new_leads:
        logger.info("✅ No new leads to process.")
        return

    # Get pipeline stages
    stages = ghl.get_pipeline_stages()
    stage_map = {s["name"]: s["id"] for s in stages}

    for lead in new_leads:
        contact_id = lead["id"]
        name = f"{lead.get('firstName', '')} {lead.get('lastName', '')}".strip()
        phone = lead.get("phone", "")
        suburb = lead.get("city", "Perth")
        tags = lead.get("tags", [])

        # Detect service type from tags
        service = "grounds maintenance"
        for tag in tags:
            if tag not in ["new-lead", "lead-processed", "owner", "seabreeze"]:
                service = tag.replace("-", " ")
                break

        logger.info(f"📋 Processing lead: {name} | {service} | {suburb}")

        try:
            # 1. Qualify the lead using Claude
            qualification = claude_ai.qualify_lead(name, service, suburb)
            score = qualification.get("score", "warm")
            sms_reply = qualification.get("response_sms", "")

            # 2. Send instant SMS reply
            if phone and sms_reply:
                ghl.send_sms(contact_id, sms_reply)
                logger.info(f"📱 SMS sent to {name}: {sms_reply}")

            # 3. Add qualification note to contact
            note = f"Lead Agent Assessment:\n• Score: {score}\n• Service: {service}\n• Suburb: {suburb}\n• Action: {qualification.get('suggested_action', 'follow_up')}\n• Auto SMS sent: Yes"
            ghl.add_note(contact_id, note)

            # 4. Create opportunity in pipeline
            stage_name = "New Lead" if score == "cold" else "Contacted"
            stage_id = stages[0]["id"] if stages else None  # Default to first stage

            if stage_id:
                ghl.create_opportunity(
                    contact_id=contact_id,
                    title=f"{name} — {service.title()} ({suburb})",
                    stage_id=stage_id,
                    value=0
                )

            # 5. Mark lead as processed
            updated_tags = [t for t in tags if t != "new-lead"] + ["lead-processed", f"score-{score}"]
            ghl.update_contact_tags(contact_id, updated_tags)

            logger.info(f"✅ Lead processed: {name} | Score: {score}")

        except Exception as e:
            logger.error(f"❌ Error processing lead {name}: {e}")

    logger.info(f"🏁 Lead Agent: Processed {len(new_leads)} leads.")
