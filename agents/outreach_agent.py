"""
Enviromentor Outreach Agent — Sydney
Sends 10 branded emails per weekday morning to Sydney prospects.
Signed by Zoe. Two CTAs: Call Zoe + Book online.
"""
import logging
import os
import requests
import anthropic
import time
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
SYDNEY_TZ = pytz.timezone("Australia/Sydney")

KEY = os.getenv("GHL_ENVIROMENTOR_KEY")
LOC = os.getenv("GHL_ENVIROMENTOR_LOCATION_ID")
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Version": "2021-07-28",
    "Content-Type": "application/json"
}

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
FROM_EMAIL = "zoe@enviromentor.com"
WEBSITE_URL = "https://enviromentor.com"
ZOE_PHONE = "0480 891 085"

SUBJECTS = {
    "strata": "Keeping Your Buildings Safe This Season — Free Property Check | Enviromentor",
    "aged care": "Protecting Your Residents — Free Property Safety Check | Enviromentor",
    "homeowner": "Your Sydney Property — Free Gutter & Garden Inspection | Enviromentor",
}

PROMPTS = {
    "strata": """Write a warm professional cold email body to a strata manager at {company} in Sydney.
From: Zoe at Enviromentor — gutter cleaning and garden maintenance specialists.
Key points: prevent water damage and liability, reduce trip hazards in common areas,
maintain property value, regular maintenance saves owners money.
Offer: free on-site assessment, no obligation.
Tone: warm, professional, Australian. 4 short sentences only.
NO subject line, NO signature — body paragraphs only.""",

    "aged care": """Write a warm professional cold email body to a facility manager at {company} aged care in Sydney.
From: Zoe at Enviromentor — gutter cleaning and garden maintenance specialists.
Key points: resident safety, falls prevention from wet leaf litter,
maintain welcoming grounds, reduce liability.
Offer: free property safety inspection.
Tone: warm, caring, professional Australian. 4 short sentences.
NO subject line, NO signature.""",

    "homeowner": """Write a warm professional cold email body to a homeowner contact at {company} in Sydney.
From: Zoe at Enviromentor — gutter cleaning and garden maintenance specialists.
Key points: protect home from water damage, keep garden looking great,
free up weekends, professional reliable service.
Offer: free property assessment and tailored quote.
Tone: warm, friendly, Australian. 4 short sentences.
NO subject line, NO signature."""
}

ACCENTS = {
    "strata": "Free Property Safety Check — Sydney Strata Specialists",
    "aged care": "Protecting Sydney's Aged Care Properties — Free Inspection",
    "homeowner": "Free Property Assessment — Sydney's Trusted Gardeners"
}

CTAS = {
    "strata": "📋 Book a Free Strata Assessment",
    "aged care": "📋 Book a Free Safety Inspection",
    "homeowner": "📋 Get Your Free Quote"
}


def build_email_html(body: str, first_name: str, ptype: str) -> str:
    paragraphs = [p.strip() for p in body.strip().split("\n") if p.strip()]
    body_html = "".join(
        f'<p style="color:#444;font-size:15px;line-height:1.7;margin:0 0 16px 0;">{p}</p>'
        for p in paragraphs
    )
    accent = ACCENTS.get(ptype, ACCENTS["homeowner"])
    cta = CTAS.get(ptype, CTAS["homeowner"])

    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f4f1e8;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1e8;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#faf8f2;border-radius:8px;overflow:hidden;box-shadow:0 4px 20px rgba(26,58,46,0.08);">
  <tr><td style="background:#1a3a2e;padding:28px 40px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td>
        <span style="color:#fff;font-size:22px;font-weight:bold;letter-spacing:-0.5px;">🌿 Enviromentor</span>
      </td>
    </tr><tr>
      <td style="padding-top:6px;"><span style="color:#7da882;font-size:12px;">Sydney's Property Care Specialists</span></td>
    </tr></table>
  </td></tr>
  <tr><td style="background:#4a8b5c;padding:10px 40px;">
    <span style="color:#fff;font-size:12px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;">{accent}</span>
  </td></tr>
  <tr><td style="padding:36px 40px 24px 40px;">
    <p style="color:#1a3a2e;font-size:16px;font-weight:bold;margin:0 0 20px 0;">Hi {first_name},</p>
    {body_html}
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
      <tr>
        <td width="48%" style="text-align:center;padding:18px 4px;background:#e1f5ee;border-radius:8px;">
          <div style="font-size:24px;margin-bottom:4px;">🏠</div>
          <div style="font-size:13px;color:#1a3a2e;font-weight:bold;">Gutter Cleaning</div>
          <div style="font-size:11px;color:#666;">Prevents water damage</div>
        </td>
        <td width="4%"></td>
        <td width="48%" style="text-align:center;padding:18px 4px;background:#e1f5ee;border-radius:8px;">
          <div style="font-size:24px;margin-bottom:4px;">🌿</div>
          <div style="font-size:13px;color:#1a3a2e;font-weight:bold;">Garden Maintenance</div>
          <div style="font-size:11px;color:#666;">Keeps property thriving</div>
        </td>
      </tr>
    </table>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:10px;">
      <tr><td align="center">
        <a href="tel:+61480891085" style="display:inline-block;background:#1a3a2e;color:#fff;text-decoration:none;padding:16px 40px;border-radius:100px;font-size:16px;font-weight:bold;">
          📞 Call Zoe Now — {ZOE_PHONE}
        </a>
      </td></tr>
    </table>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
      <tr><td align="center">
        <a href="{WEBSITE_URL}" style="display:inline-block;background:#fff;color:#1a3a2e;text-decoration:none;padding:14px 40px;border-radius:100px;font-size:15px;font-weight:bold;border:2px solid #4a8b5c;">
          {cta}
        </a>
      </td></tr>
    </table>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr><td style="border-top:1px solid #eee;"></td></tr>
    </table>
    <table cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding-right:14px;">
          <div style="width:46px;height:46px;background:#4a8b5c;border-radius:50%;text-align:center;line-height:46px;color:#fff;font-weight:bold;font-size:18px;">Z</div>
        </td>
        <td>
          <div style="color:#1a3a2e;font-weight:bold;font-size:15px;">Zoe</div>
          <div style="color:#666;font-size:12px;">Business Administrator</div>
          <div style="color:#4a8b5c;font-size:13px;font-weight:bold;">Enviromentor</div>
          <div style="color:#666;font-size:12px;margin-top:4px;">
            📞 <a href="tel:+61480891085" style="color:#4a8b5c;text-decoration:none;">{ZOE_PHONE}</a> &nbsp;|&nbsp;
            ✉️ <a href="mailto:{FROM_EMAIL}" style="color:#4a8b5c;text-decoration:none;">{FROM_EMAIL}</a>
          </div>
        </td>
      </tr>
    </table>
  </td></tr>
  <tr><td style="background:#1a3a2e;padding:18px 40px;text-align:center;">
    <p style="color:#7da882;font-size:11px;margin:0;">Enviromentor — Sydney's Property Care Specialists 🌿</p>
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""


def generate_body(company: str, ptype: str) -> str:
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        prompt = PROMPTS.get(ptype, PROMPTS["homeowner"]).format(company=company)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Claude error: {e}")
        return ("I hope this message finds you well. At Enviromentor we specialise in "
                "gutter cleaning and garden maintenance across Sydney. We'd love to offer "
                "you a complimentary property assessment — no obligation whatsoever.")


def get_pending_prospects() -> list:
    r = requests.get(
        f"https://services.leadconnectorhq.com/contacts/?locationId={LOC}&limit=100",
        headers=HEADERS
    )
    contacts = r.json().get("contacts", [])
    pending = []
    for c in contacts:
        tags = c.get("tags", [])
        name = c.get("companyName") or f"{c.get('firstName','')} {c.get('lastName','')}".strip()
        email = c.get("email", "")
        if not name or not email or "outreach-sent" in tags:
            continue
        # Determine prospect type from tags
        ptype = "homeowner"
        if "strata" in tags:
            ptype = "strata"
        elif "aged care" in tags:
            ptype = "aged care"
        elif "homeowner" in tags:
            ptype = "homeowner"
        if "new lead" in tags or "outreach-pending" in tags:
            pending.append({
                "name": name,
                "email": email,
                "id": c.get("id"),
                "type": ptype,
                "firstName": c.get("firstName") or "there"
            })
    return pending


def send_outreach(prospect: dict) -> bool:
    try:
        body = generate_body(prospect["name"], prospect["type"])
        html = build_email_html(body, prospect["firstName"], prospect["type"])
        subject = SUBJECTS.get(prospect["type"], SUBJECTS["homeowner"])

        r = requests.post(
            "https://services.leadconnectorhq.com/conversations/messages",
            headers=HEADERS,
            json={
                "type": "Email",
                "contactId": prospect["id"],
                "subject": subject,
                "html": html,
                "emailFrom": FROM_EMAIL,
                "emailTo": prospect["email"],
            }
        )

        if r.status_code in [200, 201]:
            requests.put(
                f"https://services.leadconnectorhq.com/contacts/{prospect['id']}",
                headers=HEADERS,
                json={"tags": ["outreach-sent"]}
            )
            logger.info(f"✅ Email sent to {prospect['name']}")
            return True
        elif r.status_code == 400 and "DND" in r.text:
            # Try removing DND first
            requests.put(
                f"https://services.leadconnectorhq.com/contacts/{prospect['id']}",
                headers=HEADERS,
                json={"dnd": False}
            )
            time.sleep(1)
            r2 = requests.post(
                "https://services.leadconnectorhq.com/conversations/messages",
                headers=HEADERS,
                json={
                    "type": "Email",
                    "contactId": prospect["id"],
                    "subject": subject,
                    "html": html,
                    "emailFrom": FROM_EMAIL,
                    "emailTo": prospect["email"],
                }
            )
            if r2.status_code in [200, 201]:
                requests.put(
                    f"https://services.leadconnectorhq.com/contacts/{prospect['id']}",
                    headers=HEADERS,
                    json={"tags": ["outreach-sent"]}
                )
                logger.info(f"✅ Email sent (DND removed): {prospect['name']}")
                return True
        logger.warning(f"⚠️  {prospect['name']}: {r.status_code}")
        return False
    except Exception as e:
        logger.error(f"❌ {prospect['name']}: {e}")
        return False


def run():
    """Fire 10 emails on weekday mornings 8-10am Sydney."""
    now = datetime.now(SYDNEY_TZ)
    if now.weekday() >= 5 or not (8 <= now.hour < 10):
        return

    logger.info("📧 Enviromentor Outreach: Firing branded emails...")
    pending = get_pending_prospects()

    if not pending:
        logger.info("📭 All prospects contacted!")
        return

    sent = 0
    for prospect in pending[:10]:
        if send_outreach(prospect):
            sent += 1
        time.sleep(3)

    logger.info(f"📧 Done: {sent}/{min(10,len(pending))} sent | {len(pending)-sent} remaining")
