"""
Outreach Agent — 10 branded emails per day.
Uses mini landing page style HTML template.
Signed by Zoe. Two CTAs: Call Zoe + Book online.
Fires weekdays 8-10am Perth time.
"""
import logging
import os
import requests
import anthropic
import time
import uuid
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
PERTH_TZ = pytz.timezone("Australia/Perth")

KEY = os.getenv("GHL_SEABREEZE_KEY")
LOC = os.getenv("GHL_SEABREEZE_LOCATION_ID")
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Version": "2021-07-28",
    "Content-Type": "application/json"
}

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
FROM_EMAIL = "hello@seabreezemaintenance.com.au"
WEBSITE_URL = "https://app.gohighlevel.com/v2/preview/OU8agwxXmxq3Av1xYEF8"
ZOE_PHONE = "0480 891 085"

SUBJECTS = {
    "aged-care": "Keeping Your Residents Safe — Free Property Inspection | Sea Breeze Maintenance",
    "strata": "Protecting Your Strata Portfolio — Free Quote | Sea Breeze Maintenance",
    "school": "Keeping Your Campus Safe — Free Grounds Inspection | Sea Breeze Maintenance",
}

BODY_PROMPTS = {
    "aged-care": """Write a warm professional cold email body to a facility manager at {company} aged care facility in Perth WA.
From: Zoe at Sea Breeze Maintenance
Key message: resident safety, falls prevention, liability reduction, compliance
Services: garden maintenance, preventive gutter works, pressure washing, anti-slip surfaces
Offer: Free on-site safety inspection, no obligation
Tone: warm, caring, professional Australian. 4-5 sentences only.
NO subject line, NO signature — body paragraphs only.""",

    "strata": """Write a professional cold email body to a property manager at {company} strata company in Perth WA.
From: Zoe at Sea Breeze Maintenance
Key message: liability reduction, body corporate compliance, portfolio maintenance, property presentation
Services: garden maintenance, preventive gutter works, pressure washing, anti-slip surfaces
Offer: Free quote for entire property portfolio
Tone: professional, B2B, confident but warm Australian. 4-5 sentences only.
NO subject line, NO signature — body paragraphs only.""",

    "school": """Write a professional cold email body to a facilities manager at {company} school in Perth WA.
From: Zoe at Sea Breeze Maintenance
Key message: student safety, campus presentation, duty of care, grounds maintenance
Services: anti-slip surfaces, preventive gutter works, pressure washing, garden maintenance
Offer: Free on-site grounds safety inspection
Tone: professional, safety-focused, warm Australian. 4-5 sentences only.
NO subject line, NO signature — body paragraphs only.""",
}

CTA_LABELS = {
    "aged-care": "📋 Book a Free Safety Inspection",
    "strata": "📋 Request a Free Portfolio Quote",
    "school": "📋 Book a Free Grounds Inspection",
}

ACCENT_BARS = {
    "aged-care": "Free On-Site Safety Inspection — No Obligation",
    "strata": "Free Portfolio Quote — Perth &amp; South West WA",
    "school": "Free Grounds Safety Inspection — Perth Schools",
}


def build_email_html(body: str, first_name: str, ptype: str) -> str:
    """Build branded HTML email matching website style."""
    paragraphs = [p.strip() for p in body.strip().split("\n") if p.strip()]
    body_html = "".join(
        f'<p style="color:#444;font-size:15px;line-height:1.7;margin:0 0 16px 0;">{p}</p>'
        for p in paragraphs
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

  <tr><td style="background:#1a1a2e;padding:28px 40px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td><div style="display:inline-block;background:#1D9E75;border-radius:50%;width:44px;height:44px;line-height:44px;text-align:center;color:#fff;font-weight:bold;font-size:18px;vertical-align:middle;">SB</div>
      <span style="color:#fff;font-size:20px;font-weight:bold;margin-left:12px;vertical-align:middle;">Sea Breeze Maintenance</span></td>
    </tr><tr>
      <td style="padding-top:6px;"><span style="color:#9FE1CB;font-size:12px;">Property Safety Specialists — Perth &amp; South West WA</span></td>
    </tr></table>
  </td></tr>

  <tr><td style="background:#1D9E75;padding:10px 40px;">
    <span style="color:#fff;font-size:12px;letter-spacing:1px;text-transform:uppercase;font-weight:bold;">{ACCENT_BARS[ptype]}</span>
  </td></tr>

  <tr><td style="padding:36px 40px 24px 40px;">
    <p style="color:#1a1a2e;font-size:16px;font-weight:bold;margin:0 0 20px 0;">Hi {first_name},</p>
    {body_html}

    <!-- Services -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
      <tr>
        <td width="25%" style="text-align:center;padding:12px 4px;background:#E1F5EE;border-radius:6px;">
          <div style="font-size:20px;margin-bottom:4px;">🌿</div>
          <div style="font-size:10px;color:#1D9E75;font-weight:bold;line-height:1.3;">Garden<br>Maintenance</div>
        </td>
        <td width="2%"></td>
        <td width="25%" style="text-align:center;padding:12px 4px;background:#E1F5EE;border-radius:6px;">
          <div style="font-size:20px;margin-bottom:4px;">🏠</div>
          <div style="font-size:10px;color:#1D9E75;font-weight:bold;line-height:1.3;">Preventive<br>Gutter Works</div>
        </td>
        <td width="2%"></td>
        <td width="25%" style="text-align:center;padding:12px 4px;background:#E1F5EE;border-radius:6px;">
          <div style="font-size:20px;margin-bottom:4px;">💧</div>
          <div style="font-size:10px;color:#1D9E75;font-weight:bold;line-height:1.3;">Pressure<br>Washing</div>
        </td>
        <td width="2%"></td>
        <td width="25%" style="text-align:center;padding:12px 4px;background:#E1F5EE;border-radius:6px;">
          <div style="font-size:20px;margin-bottom:4px;">🦺</div>
          <div style="font-size:10px;color:#1D9E75;font-weight:bold;line-height:1.3;">Anti-Slip<br>Surfaces</div>
        </td>
      </tr>
    </table>

    <!-- Primary CTA -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:10px;">
      <tr><td align="center">
        <a href="tel:+61480891085" style="display:inline-block;background:#1D9E75;color:#fff;text-decoration:none;padding:16px 40px;border-radius:6px;font-size:16px;font-weight:bold;">
          📞 Call Zoe Now — {ZOE_PHONE}
        </a>
      </td></tr>
    </table>

    <!-- Secondary CTA -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
      <tr><td align="center">
        <a href="{WEBSITE_URL}" style="display:inline-block;background:#fff;color:#1D9E75;text-decoration:none;padding:14px 40px;border-radius:6px;font-size:15px;font-weight:bold;border:2px solid #1D9E75;">
          {CTA_LABELS[ptype]}
        </a>
      </td></tr>
    </table>

    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr><td style="border-top:1px solid #eee;"></td></tr>
    </table>

    <!-- Signature -->
    <table cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding-right:14px;">
          <div style="width:46px;height:46px;background:#1D9E75;border-radius:50%;text-align:center;line-height:46px;color:#fff;font-weight:bold;font-size:18px;">Z</div>
        </td>
        <td>
          <div style="color:#1a1a2e;font-weight:bold;font-size:15px;">Zoe</div>
          <div style="color:#666;font-size:12px;">Business Administrator</div>
          <div style="color:#1D9E75;font-size:13px;font-weight:bold;">Sea Breeze Maintenance</div>
          <div style="color:#666;font-size:12px;margin-top:4px;">
            📞 <a href="tel:+61480891085" style="color:#1D9E75;text-decoration:none;">{ZOE_PHONE}</a> &nbsp;|&nbsp;
            ✉️ <a href="mailto:{FROM_EMAIL}" style="color:#1D9E75;text-decoration:none;">{FROM_EMAIL}</a>
          </div>
        </td>
      </tr>
    </table>
  </td></tr>

  <tr><td style="background:#1a1a2e;padding:18px 40px;text-align:center;">
    <p style="color:#9FE1CB;font-size:11px;margin:0 0 4px 0;">Sea Breeze Maintenance Pty Ltd — Perth &amp; South West WA</p>
    <p style="color:#555;font-size:10px;margin:0;">
      You're receiving this because we believe we can help keep your property safe. &nbsp;
      <a href="#" style="color:#555;">Unsubscribe</a>
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""


def generate_body(company: str, ptype: str) -> str:
    """Generate personalised email body using Claude."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": BODY_PROMPTS[ptype].format(company=company)}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Claude error: {e}")
        return ("I hope this message finds you well. At Sea Breeze Maintenance, "
                "we specialise in property safety services across Perth and South West WA. "
                "We'd love to offer you a complimentary inspection — no obligation whatsoever.")


def get_pending_prospects() -> list:
    """Get contacts pending outreach."""
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
        if any(t in tags for t in ["aged-care-prospect", "strata-prospect",
                                    "school-prospect", "outreach-pending"]):
            ptype = ("aged-care" if "aged-care-prospect" in tags
                     else "strata" if "strata-prospect" in tags else "school")
            pending.append({
                "name": name,
                "email": email,
                "id": c.get("id"),
                "type": ptype,
                "firstName": c.get("firstName", "there")
            })
    return pending


def send_outreach(prospect: dict) -> bool:
    """Send branded outreach email."""
    try:
        body = generate_body(prospect["name"], prospect["type"])
        html = build_email_html(body, prospect["firstName"] or "there", prospect["type"])
        subject = SUBJECTS[prospect["type"]]

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
            # Tag as sent
            requests.put(
                f"https://services.leadconnectorhq.com/contacts/{prospect['id']}",
                headers=HEADERS,
                json={"tags": ["outreach-sent"]}
            )
            requests.post(
                f"https://services.leadconnectorhq.com/contacts/{prospect['id']}/notes",
                headers=HEADERS,
                json={"body": f"Outreach email sent\nSubject: {subject}"}
            )
            logger.info(f"✅ Email sent to {prospect['name']}")
            return True
        else:
            logger.warning(f"⚠️  {prospect['name']}: {r.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ {prospect['name']}: {e}")
        return False


def run():
    """Fire 10 emails on weekday mornings 8-10am Perth."""
    now = datetime.now(PERTH_TZ)
    if now.weekday() >= 5 or not (8 <= now.hour < 10):
        return

    logger.info("📧 Outreach Agent: Firing branded emails...")
    pending = get_pending_prospects()

    if not pending:
        logger.info("📭 All prospects contacted!")
        return

    sent = 0
    for prospect in pending[:10]:
        if send_outreach(prospect):
            sent += 1
        time.sleep(3)

    logger.info(f"📧 Done: {sent}/10 sent | {len(pending)-sent} remaining")
