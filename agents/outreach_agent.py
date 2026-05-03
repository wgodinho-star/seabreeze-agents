"""
Outreach Agent — B2B prospecting for aged care and strata.
Finds prospects, sends personalised emails, follows up automatically.
Francisco only gets notified when someone responds.
"""
import logging
import os
import requests
from datetime import datetime, timedelta
import pytz
from tools import claude_ai, ghl

logger = logging.getLogger(__name__)
PERTH_TZ = pytz.timezone("Australia/Perth")

KEY = os.getenv("GHL_SEABREEZE_KEY")
LOC = os.getenv("GHL_SEABREEZE_LOCATION_ID")
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Version": "2021-07-28",
    "Content-Type": "application/json"
}

FRANCISCO_NAME = "Francisco Da Silva"
BUSINESS_NAME = "Sea Breeze Maintenance"
FRANCISCO_PHONE = os.getenv("CLIENT_PHONE", "+61404590230")
FRANCISCO_EMAIL = os.getenv("CLIENT_EMAIL", "accounts@seabreezemaintenance.com.au")
WEBSITE = "seabreezemaintenance.com.au"

AGED_CARE_PROSPECTS = [
    {"company": "Amana Living", "email": "info@amanaliving.org.au",
     "phone": "+61894574999", "contact_id": "k07cV1m7XqJO08jM7IAs"},
    {"company": "Bethanie Group", "email": "info@bethanie.org.au",
     "phone": "+61893165500", "contact_id": "mGcQqWzkIweKYic9IGnl"},
    {"company": "Southern Cross Care WA", "email": "enquiries@sccwa.com.au",
     "phone": "+61893618111", "contact_id": "ZWUq6z5dt7YWMvv99d0a"},
]

STRATA_PROSPECTS = [
    {"company": "CBRE Strata Perth", "email": "perth@cbre.com.au",
     "phone": "+61892624000", "contact_id": "qsjFOf1oMhOwOSjRYeTB"},
    {"company": "Colliers International Perth", "email": "perth@colliers.com.au",
     "phone": "+61892627666", "contact_id": "hgIXJYve7aA3ih3T4zQV"},
]


def generate_email(company: str, prospect_type: str) -> dict:
    """Generate a personalised outreach email using Claude."""
    if prospect_type == "aged-care":
        content = claude_ai.think(
            system_prompt=f"""You write professional, warm cold outreach emails for {BUSINESS_NAME}.
Owner: {FRANCISCO_NAME}. Perth & Dunsborough WA. Fully insured.
Services: gutter cleaning, anti-slip surfaces, pressure washing, garden maintenance.
Focus: resident safety, falls prevention, compliance for aged care.""",
            user_message=f"""Write a cold outreach email to the facility manager at {company} Perth WA.
Subject line + email body. 4-5 sentences. Offer free safety inspection.
Sign off as {FRANCISCO_NAME}, {BUSINESS_NAME}.
Phone: {FRANCISCO_PHONE} | Email: {FRANCISCO_EMAIL} | Web: {WEBSITE}""",
            max_tokens=300
        )
    else:
        content = claude_ai.think(
            system_prompt=f"""You write professional B2B cold outreach emails for {BUSINESS_NAME}.
Owner: {FRANCISCO_NAME}. Perth & Dunsborough WA. Fully insured.
Services: gutter cleaning, anti-slip surfaces, pressure washing, grounds maintenance.
Focus: liability reduction, compliance, body corporate property management.""",
            user_message=f"""Write a cold outreach email to the property manager at {company} Perth WA.
Subject line + email body. 4-5 sentences. Offer free quote for portfolio.
Sign off as {FRANCISCO_NAME}, {BUSINESS_NAME}.
Phone: {FRANCISCO_PHONE} | Email: {FRANCISCO_EMAIL} | Web: {WEBSITE}""",
            max_tokens=300
        )
    
    lines = content.strip().split('\n')
    subject = ""
    body_lines = []
    
    for i, line in enumerate(lines):
        if line.lower().startswith("subject:") or line.startswith("**Subject"):
            subject = line.replace("**Subject:**", "").replace("Subject:", "").strip().strip("*")
        else:
            body_lines.append(line)
    
    return {
        "subject": subject or f"Property Safety Services for {company} – Sea Breeze Maintenance",
        "body": "\n".join(body_lines).strip()
    }


def send_outreach_email(contact_id: str, company: str,
                        email_address: str, prospect_type: str) -> bool:
    """Send outreach email via GHL."""
    try:
        email = generate_email(company, prospect_type)
        
        r = requests.post(
            f"https://services.leadconnectorhq.com/conversations/messages/outbound",
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
        
        if r.status_code in [200, 201]:
            ghl.add_note(contact_id,
                f"Outreach Agent: Email sent {datetime.now(PERTH_TZ).strftime('%d %b %Y')}\n"
                f"Subject: {email['subject']}")
            ghl.update_contact_tags(contact_id, 
                ["aged-care-prospect" if prospect_type == "aged-care" else "strata-prospect",
                 "outreach-sent"])
            logger.info(f"✅ Email sent to {company}")
            return True
        else:
            logger.warning(f"⚠️ Email API returned {r.status_code} for {company}")
            ghl.add_note(contact_id,
                f"Outreach Agent: Email ready to send manually.\n"
                f"Subject: {email['subject']}\n"
                f"Body:\n{email['body']}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending to {company}: {e}")
        return False


def check_for_replies() -> list:
    """Check for any replies from prospects."""
    replied = []
    all_prospects = AGED_CARE_PROSPECTS + STRATA_PROSPECTS
    
    for prospect in all_prospects:
        try:
            convos = ghl.get_conversations(prospect["contact_id"])
            for convo in convos:
                if convo.get("unreadCount", 0) > 0:
                    replied.append({
                        "company": prospect["company"],
                        "contact_id": prospect["contact_id"]
                    })
                    break
        except Exception:
            pass
    
    return replied


def run():
    """Main outreach agent loop."""
    logger.info("📧 Outreach Agent: Running...")
    now = datetime.now(PERTH_TZ)
    
    # Only run outreach on weekday mornings 8-10am
    if now.weekday() >= 5:
        logger.info("📧 Weekend — skipping outreach.")
        return
    
    if not (8 <= now.hour < 10):
        # Still check for replies at any time
        replies = check_for_replies()
        if replies:
            for r in replies:
                msg = (f"📧 PROSPECT REPLIED: {r['company']} has responded "
                       f"to your outreach! Check GHL conversations now.")
                ghl.add_note(r["contact_id"], "Outreach Agent: Reply detected!")
                logger.info(f"🎉 Reply from {r['company']}!")
        return
    
    # Morning outreach window — send to pending prospects
    all_prospects = [
        (p, "aged-care") for p in AGED_CARE_PROSPECTS
    ] + [
        (p, "strata") for p in STRATA_PROSPECTS
    ]
    
    sent_count = 0
    for prospect, ptype in all_prospects:
        contacts = ghl.get_contacts(limit=100)
        contact = next(
            (c for c in contacts if c.get("id") == prospect["contact_id"]),
            None
        )
        
        if contact and "outreach-sent" not in contact.get("tags", []):
            success = send_outreach_email(
                prospect["contact_id"],
                prospect["company"],
                prospect["email"],
                ptype
            )
            if success:
                sent_count += 1
    
    # Check for replies
    replies = check_for_replies()
    for reply in replies:
        logger.info(f"🎉 REPLY detected from {reply['company']}!")
    
    logger.info(f"📧 Outreach Agent: {sent_count} emails sent, "
                f"{len(replies)} replies detected.")
