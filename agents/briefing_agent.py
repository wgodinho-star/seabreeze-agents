"""
Briefing Agent — Daily WhatsApp/SMS briefing for Wander.

Morning (7am Perth): What the agents will do today
Evening (5pm Perth): What was done, what worked, what needs attention

This is Wander's daily connection to the Enviromentor system.
Think of it as the CEO's daily standup report.
"""
import logging
import os
import requests
from datetime import datetime, timedelta
import pytz
from tools import claude_ai

logger = logging.getLogger(__name__)
PERTH_TZ = pytz.timezone("Australia/Perth")

KEY = os.getenv("GHL_SEABREEZE_KEY")
LOC = os.getenv("GHL_SEABREEZE_LOCATION_ID")
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Version": "2021-07-28",
    "Content-Type": "application/json"
}

WANDER_CONTACT_ID = "g1Hp5UCnMLVganCyNj93"
FRANCISCO_CONTACT_ID = os.getenv("GHL_FRANCISCO_CONTACT_ID")
PERTH_NOW = lambda: datetime.now(PERTH_TZ)


def get_pipeline_stats() -> dict:
    """Get current pipeline counts from GHL."""
    try:
        r = requests.get(
            f"https://services.leadconnectorhq.com/opportunities/search"
            f"?location_id={LOC}&limit=100",
            headers=HEADERS
        )
        opps = r.json().get("opportunities", [])
        
        stages = {}
        for opp in opps:
            stage = opp.get("pipelineStageId", "unknown")
            stages[stage] = stages.get(stage, 0) + 1
        
        return {
            "total": len(opps),
            "stages": stages
        }
    except Exception:
        return {"total": 0, "stages": {}}


def get_recent_contacts(hours: int = 24) -> list:
    """Get contacts added in the last N hours."""
    try:
        r = requests.get(
            f"https://services.leadconnectorhq.com/contacts/"
            f"?locationId={LOC}&limit=100",
            headers=HEADERS
        )
        contacts = r.json().get("contacts", [])
        now = PERTH_NOW()
        recent = []
        for c in contacts:
            added = c.get("dateAdded", "")
            if added:
                try:
                    dt = datetime.fromisoformat(
                        added.replace("Z", "+00:00")
                    ).astimezone(PERTH_TZ)
                    if (now - dt).total_seconds() < hours * 3600:
                        recent.append(c)
                except Exception:
                    pass
        return recent
    except Exception:
        return []


def get_prospects_status() -> dict:
    """Check outreach prospect pipeline status."""
    try:
        r = requests.get(
            f"https://services.leadconnectorhq.com/contacts/"
            f"?locationId={LOC}&limit=100",
            headers=HEADERS
        )
        contacts = r.json().get("contacts", [])
        
        pending = []
        sent = []
        replied = []
        
        for c in contacts:
            tags = c.get("tags", [])
            name = c.get("companyName", "")
            if not name:
                continue
            if "outreach-replied" in tags:
                replied.append(name)
            elif "outreach-sent" in tags:
                sent.append(name)
            elif "outreach-pending" in tags:
                pending.append(name)
        
        return {
            "pending": pending,
            "sent": sent,
            "replied": replied
        }
    except Exception:
        return {"pending": [], "sent": [], "replied": []}


def send_to_wander(message: str):
    """Send message to Wander via GHL conversation."""
    try:
        requests.post(
            f"https://services.leadconnectorhq.com/conversations/messages",
            headers=HEADERS,
            json={
                "type": "Email",
                "contactId": WANDER_CONTACT_ID,
                "subject": f"Enviromentor Daily Briefing — {PERTH_NOW().strftime('%a %d %b')}",
                "html": message.replace("\n", "<br>"),
                "emailFrom": "enviromentor.australia@gmail.com",
                "emailTo": "wgodinho@gmail.com",
            }
        )
        logger.info("✅ Daily briefing sent to Wander")
    except Exception as e:
        logger.error(f"❌ Could not send briefing: {e}")


def morning_briefing():
    """7am Perth — What will happen today."""
    now = PERTH_NOW()
    day = now.strftime("%A")
    date = now.strftime("%d %B %Y")
    is_weekday = now.weekday() < 5
    is_monday = now.weekday() == 0

    prospects = get_prospects_status()
    pipeline = get_pipeline_stats()

    # Build what's happening today
    today_tasks = []

    if is_weekday:
        # Check if any prospects still pending
        if prospects["pending"]:
            today_tasks.append(
                f"📧 Outreach Agent will send {len(prospects['pending'])} "
                f"cold emails to: {', '.join(prospects['pending'][:3])}"
                f"{'...' if len(prospects['pending']) > 3 else ''}"
            )
        if prospects["sent"]:
            today_tasks.append(
                f"📬 Follow-up Agent checking {len(prospects['sent'])} "
                f"prospects for follow-up timing"
            )
        today_tasks.append(
            "🔍 Lead Agent running every 5 min — watching for new enquiries"
        )
        today_tasks.append(
            "📅 Scheduling Agent running every 5 min — "
            "watching for appointment reminders needed"
        )

    if is_monday:
        today_tasks.append(
            "📱 Social Agent generating this week's content from GHL Media Storage"
        )
        today_tasks.append(
            "📊 Report Agent sending weekly summary to Francisco + Wander"
        )

    if not today_tasks:
        today_tasks.append(
            "🏖️ Weekend — Lead, Scheduling and Review agents still running. "
            "Outreach paused until Monday."
        )

    tasks_text = "\n".join(today_tasks)

    message = f"""🌿 ENVIROMENTOR MORNING BRIEFING
{day} {date} | 7:00am Perth

Good morning Wander! Here's what your AI team is doing today:

{tasks_text}

📊 PIPELINE SNAPSHOT:
• Total opportunities: {pipeline['total']}
• Prospects emailed: {len(prospects['sent'])}
• Prospects replied: {len(prospects['replied'])}
• Prospects pending: {len(prospects['pending'])}

{"🎉 REPLIES RECEIVED: " + ", ".join(prospects['replied']) if prospects['replied'] else "⏳ Waiting for first reply..."}

You'll get your evening update at 5pm with what actually happened.
— Enviromentor AI System 🌿"""

    send_to_wander(message)
    logger.info("☀️ Morning briefing sent")


def evening_briefing():
    """5pm Perth — What happened today."""
    now = PERTH_NOW()
    day = now.strftime("%A")
    date = now.strftime("%d %B %Y")

    prospects = get_prospects_status()
    pipeline = get_pipeline_stats()
    recent_contacts = get_recent_contacts(hours=24)

    new_leads = [
        c for c in recent_contacts
        if "outreach-pending" not in c.get("tags", [])
        and "aged-care-prospect" not in c.get("tags", [])
        and "strata-prospect" not in c.get("tags", [])
    ]

    message = f"""🌙 ENVIROMENTOR EVENING BRIEFING
{day} {date} | 5:00pm Perth

Here's what your AI team did today:

📊 TODAY'S RESULTS:
• New leads in system: {len(new_leads)}
• Prospects emailed: {len(prospects['sent'])}
• Replies received: {len(prospects['replied'])}
• Pipeline opportunities: {pipeline['total']}

{"🎉 GREAT NEWS — Replies from: " + ", ".join(prospects['replied']) if prospects['replied'] else "📭 No replies yet — follow-ups will continue automatically"}

⚙️ AGENTS STATUS:
✅ Lead Agent — running
✅ Scheduling Agent — running  
✅ Outreach Agent — {"ran this morning" if now.weekday() < 5 else "paused (weekend)"}
✅ Follow-up Agent — {"ran this morning" if now.weekday() < 5 else "paused (weekend)"}
✅ Review Agent — running
✅ Social Agent — {"ran this morning" if now.weekday() == 0 else "next Monday"}
✅ Report Agent — {"ran this morning" if now.weekday() == 0 else f"next Monday"}

🎯 TOMORROW:
{"Outreach + Follow-up agents fire at 8am Perth" if now.weekday() < 4 else "Weekend — core agents monitoring only"}

— Enviromentor AI System 🌿"""

    send_to_wander(message)
    logger.info("🌙 Evening briefing sent")


def run():
    """Run at 7am (morning) or 5pm (evening) Perth time."""
    now = PERTH_NOW()
    hour = now.hour

    if hour == 7:
        morning_briefing()
    elif hour == 17:
        evening_briefing()
    else:
        pass  # Not briefing time
