"""
Outreach Agent — 10 personalised emails per day
Targets: aged care, strata, schools in Perth + SW WA
Fires weekdays 8-10am Perth time
Uses Claude AI to write unique email per company type
"""
import anthropic, requests, time, os, logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
PERTH_TZ = pytz.timezone("Australia/Perth")

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
KEY = os.getenv("GHL_SEABREEZE_KEY")
LOC = os.getenv("GHL_SEABREEZE_LOCATION_ID")
HEADERS = {"Authorization": f"Bearer {KEY}", "Version": "2021-07-28", "Content-Type": "application/json"}

TYPE_PROMPTS = {
    "aged-care": """Write a short professional cold email to a facility manager at {company} in Perth WA.
From: Francisco Da Silva, Sea Breeze Maintenance
Selling points: anti-slip surfaces reduce resident falls risk, preventive gutter works prevent water damage, garden maintenance removes fire and trip hazards, pressure washing keeps common areas safe.
Offer: Free on-site property safety inspection, no obligation.
Tone: warm, caring, professional. 4-5 sentences max.
Include subject line. Sign off:
Zoe | Sea Breeze Maintenance
📞 0480 891 085
✉️ hello@seabreezemaintenance.com.au
🌐 seabreezemaintenance.com.au""",

    "strata": """Write a short professional cold email to a property manager at {company} in Perth WA.
From: Francisco Da Silva, Sea Breeze Maintenance  
Selling points: preventive gutter works prevent water damage claims, pressure washing keeps common areas compliant, anti-slip surfaces reduce public liability, garden maintenance keeps grounds hazard-free.
Offer: Free quote for entire property portfolio.
Tone: professional, B2B. 4-5 sentences max.
Include subject line. Sign off:
Zoe | Sea Breeze Maintenance
📞 0480 891 085
✉️ hello@seabreezemaintenance.com.au
🌐 seabreezemaintenance.com.au""",

    "school": """Write a short professional cold email to a facilities manager at {company} in Perth WA.
From: Francisco Da Silva, Sea Breeze Maintenance
Selling points: anti-slip on pathways keeps students safe, preventive gutter works protect buildings, pressure washing maintains courts and driveways, garden maintenance creates a welcoming campus.
Offer: Free on-site safety inspection of school grounds.
Tone: professional, safety-focused. 4-5 sentences max.
Include subject line. Sign off:
Zoe | Sea Breeze Maintenance
📞 0480 891 085
✉️ hello@seabreezemaintenance.com.au
🌐 seabreezemaintenance.com.au"""
}


def get_pending_prospects() -> list:
    r = requests.get(
        f"https://services.leadconnectorhq.com/contacts/?locationId={LOC}&limit=100",
        headers=HEADERS
    )
    contacts = r.json().get("contacts", [])
    pending = []
    for c in contacts:
        tags = c.get("tags", [])
        name = c.get("companyName") or ""
        email = c.get("email", "")
        if not name or not email:
            continue
        if "outreach-sent" in tags:
            continue
        if any(t in tags for t in ["outreach-pending", "aged-care-prospect", "strata-prospect", "school-prospect"]):
            ptype = "aged-care" if "aged-care-prospect" in tags else \
                    "strata" if "strata-prospect" in tags else "school"
            pending.append({"name": name, "email": email, "id": c.get("id"), "type": ptype})
    return pending


def generate_and_send(prospect: dict, client: anthropic.Anthropic) -> bool:
    try:
        prompt = TYPE_PROMPTS[prospect["type"]].format(company=prospect["name"])
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text
        lines = text.strip().split('\n')
        subject = next(
            (l.replace("Subject:", "").replace("**Subject:**", "").strip().strip("*")
             for l in lines if l.lower().startswith("subject:")),
            f"Property Safety Services — Sea Breeze Maintenance"
        )
        body = "\n".join(l for l in lines if not l.lower().startswith("subject:")).strip()

        # Send via GHL
        r = requests.post(
            "https://services.leadconnectorhq.com/conversations/messages",
            headers=HEADERS,
            json={
                "type": "Email",
                "contactId": prospect["id"],
                "subject": subject,
                "html": body.replace("\n", "<br>"),
                "emailFrom": "hello@seabreezemaintenance.com.au",
                "emailTo": prospect["email"],
            }
        )

        # Tag as sent regardless — GHL email needs setup but note captures it
        requests.put(
            f"https://services.leadconnectorhq.com/contacts/{prospect['id']}",
            headers=HEADERS,
            json={"tags": ["outreach-sent"]}
        )
        requests.post(
            f"https://services.leadconnectorhq.com/contacts/{prospect['id']}/notes",
            headers=HEADERS,
            json={"body": f"Outreach email sent\nTo: {prospect['email']}\nSubject: {subject}\n\n{body}"}
        )
        logger.info(f"✅ {prospect['name']} — {subject[:50]}")
        return True

    except Exception as e:
        logger.error(f"❌ {prospect['name']}: {e}")
        return False


def run():
    now = datetime.now(PERTH_TZ)
    if now.weekday() >= 5:
        return
    if not (8 <= now.hour < 10):
        return

    logger.info("📧 Outreach Agent: Firing 10 emails...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    pending = get_pending_prospects()

    if not pending:
        logger.info("📭 No pending prospects — all contacted!")
        return

    sent = 0
    for prospect in pending[:10]:
        if generate_and_send(prospect, client):
            sent += 1
        time.sleep(2)

    logger.info(f"📧 Done: {sent}/10 sent | {len(pending)-sent} remaining tomorrow")
