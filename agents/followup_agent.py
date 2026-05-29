"""
Follow-up Agent — automated email sequence for prospects.
Day 1: Introduction (Outreach Agent handles this)
Day 4: Gentle follow-up
Day 10: Value-add content
Day 21: Final nudge

Most deals close on follow-up 2 or 3 — not the first email.
"""
import logging
import os
import requests
from datetime import datetime, timedelta
import pytz
from tools import claude_ai

logger = logging.getLogger(__name__)
SYDNEY_TZ = pytz.timezone("Australia/Sydney")

KEY = os.getenv("GHL_ENVIROMENTOR_KEY")
LOC = os.getenv("GHL_ENVIROMENTOR_LOCATION_ID")
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Version": "2021-07-28",
    "Content-Type": "application/json"
}

FRANCISCO_EMAIL = os.getenv("CLIENT_EMAIL", "accounts@enviromentormaintenance.com.au")
FRANCISCO_PHONE = os.getenv("CLIENT_PHONE", "+61404590230")
WEBSITE = "enviromentormaintenance.com.au"


def days_since_tag(contact: dict, tag_prefix: str) -> int:
    """Estimate days since a tag was added (approximate via contact date)."""
    # GHL doesn't store tag timestamps easily, so we use contact dateAdded
    # In production this would use a custom field with timestamp
    date_added = contact.get("dateAdded", "")
    if not date_added:
        return 0
    try:
        added = datetime.fromisoformat(
            date_added.replace("Z", "+00:00")
        ).astimezone(SYDNEY_TZ)
        return (datetime.now(SYDNEY_TZ) - added).days
    except Exception:
        return 0


def generate_followup_email(company: str, prospect_type: str,
                             followup_num: int) -> dict:
    """Generate a follow-up email using Claude."""
    
    if followup_num == 2:
        prompt = f"""Write a short, warm follow-up email (follow-up #2, sent 4 days after initial outreach) 
to a {'facility manager at an aged care facility' if prospect_type == 'aged-care' else 'property manager at a strata company'} 
at {company} in Sydney NSW.

From Francisco Da Silva, Enviromentor.
Reference the previous email briefly. 
Add a soft reason why NOW is a good time (e.g. approaching winter = gutter cleaning season, 
wet season = slip hazards increase).
Keep it to 3-4 sentences. No hard sell. 
Subject line included.
Sign off: Francisco Da Silva | Enviromentor | 0404 590 230 | Powered by Stackd AI AI"""

    elif followup_num == 3:
        prompt = f"""Write a value-add follow-up email (follow-up #3, sent 10 days after initial outreach) 
to a {'facility manager at an aged care facility' if prospect_type == 'aged-care' else 'property manager at a strata company'} 
at {company} in Sydney NSW.

From Francisco Da Silva, Enviromentor.
Share one useful insight — e.g. "Did you know blocked gutters are the #1 cause of water damage claims 
in Sydney properties?" or "Falls in aged care are 3x more likely on wet outdoor surfaces."
Make it genuinely useful, not salesy.
Offer the free inspection again casually at the end.
Keep it to 4-5 sentences.
Subject line included.
Sign off: Francisco Da Silva | Enviromentor | 0404 590 230 | Powered by Stackd AI AI"""

    else:  # followup_num == 4, day 21
        prompt = f"""Write a final follow-up email (follow-up #4, sent 21 days after initial outreach) 
to a {'facility manager at an aged care facility' if prospect_type == 'aged-care' else 'property manager at a strata company'} 
at {company} in Sydney NSW.

From Francisco Da Silva, Enviromentor.
This is the last email — make it brief, leave the door open, no pressure.
Something like "I'll leave the ball in your court — if the timing is ever right, 
we'd love to help keep your property safe."
Warm and human. 3 sentences max.
Subject line included.
Sign off: Francisco Da Silva | Enviromentor | 0404 590 230 | Powered by Stackd AI AI"""

    content = claude_ai.think(
        system_prompt="You write warm, professional follow-up emails for a property maintenance business in Sydney NSW.",
        user_message=prompt,
        max_tokens=300
    )

    lines = content.strip().split('\n')
    subject = ""
    body_lines = []
    for line in lines:
        if "subject:" in line.lower() or line.startswith("**Subject"):
            subject = line.replace("**Subject:**", "").replace(
                "Subject:", "").strip().strip("*")
        else:
            body_lines.append(line)

    return {
        "subject": subject or f"Re: Property Safety Services – {company}",
        "body": "\n".join(body_lines).strip()
    }


def send_followup(contact_id: str, company: str,
                  email_address: str, prospect_type: str,
                  followup_num: int) -> bool:
    """Send a follow-up email via GHL."""
    try:
        email = generate_followup_email(company, prospect_type, followup_num)

        r = requests.post(
            "https://services.leadconnectorhq.com/conversations/messages",
            headers=HEADERS,
            json={
                "type": "Email",
                "contactId": contact_id,
                "subject": email["subject"],
                "html": email["body"].replace("\n", "<br>"),
                "emailFrom": FRANCISCO_EMAIL,
                "emailTo": email_address,
            }
        )

        tag = f"followup-{followup_num}-sent"
        requests.put(
            f"https://services.leadconnectorhq.com/contacts/{contact_id}",
            headers=HEADERS,
            json={"tags": [tag]}
        )

        # Add note
        requests.post(
            f"https://services.leadconnectorhq.com/contacts/{contact_id}/notes",
            headers=HEADERS,
            json={"body": f"Follow-up #{followup_num} sent: {email['subject']}"}
        )

        logger.info(f"✅ Follow-up #{followup_num} sent to {company}")
        return True

    except Exception as e:
        logger.error(f"❌ Follow-up error for {company}: {e}")
        return False


def run():
    """Check all prospects and send follow-ups based on timing."""
    logger.info("📬 Follow-up Agent: Checking sequences...")

    # Only run weekday mornings
    now = datetime.now(SYDNEY_TZ)
    if now.weekday() >= 5 or not (8 <= now.hour < 11):
        return

    # Get all outreach contacts
    r = requests.get(
        f"https://services.leadconnectorhq.com/contacts/?locationId={LOC}&limit=100",
        headers=HEADERS
    )
    contacts = r.json().get("contacts", [])

    outreach_contacts = [
        c for c in contacts
        if "outreach-sent" in c.get("tags", [])
        and "outreach-replied" not in c.get("tags", [])
    ]

    sent_count = 0
    for contact in outreach_contacts:
        tags = contact.get("tags", [])
        contact_id = contact.get("id")
        company = contact.get("companyName", "your team")
        email = contact.get("email", "")
        days = days_since_tag(contact, "outreach-sent")

        ptype = "aged-care" if "aged-care-prospect" in tags else "strata"

        if not email:
            continue

        # Determine which follow-up to send
        if days >= 4 and "followup-2-sent" not in tags:
            send_followup(contact_id, company, email, ptype, 2)
            sent_count += 1
        elif days >= 10 and "followup-3-sent" not in tags:
            send_followup(contact_id, company, email, ptype, 3)
            sent_count += 1
        elif days >= 21 and "followup-4-sent" not in tags:
            send_followup(contact_id, company, email, ptype, 4)
            sent_count += 1

    logger.info(f"📬 Follow-up Agent: {sent_count} follow-ups sent.")
