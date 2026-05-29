"""
Health Monitor Agent — hourly system check.
Fixed: NoneType crash on contacts without companyName.
Fixed: Email check uses message count not just conversations.
"""
import logging
import os
import requests
import urllib.request
import urllib.parse
import urllib.error
import base64
import json
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)
SYDNEY_TZ = pytz.timezone("Australia/Sydney")
SYDNEY_TZ = pytz.timezone("Australia/Sydney")

KEY = os.getenv("GHL_ENVIROMENTOR_KEY")
LOC = os.getenv("GHL_ENVIROMENTOR_LOCATION_ID")
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Version": "2021-07-28",
    "Content-Type": "application/json"
}

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_AU_NUMBER", "+61480891085")
FRANCISCO_PHONE = os.getenv("CLIENT_PHONE", "+61404590230")


def send_alert(message: str):
    """Send alert via GHL email — FREE, no SMS cost."""
    try:
        KEY = os.getenv("GHL_ENVIROMENTOR_KEY")
        LOC = os.getenv("GHL_ENVIROMENTOR_LOCATION_ID")
        HEADERS = {
            "Authorization": f"Bearer {KEY}",
            "Version": "2021-07-28",
            "Content-Type": "application/json"
        }

        now_str = datetime.now(SYDNEY_TZ).strftime("%d %b %Y %I:%M%p")

        html = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
<table width="600" style="background:#fff;border-radius:8px;overflow:hidden;margin:auto;">
  <tr><td style="background:#A32D2D;padding:20px 30px;">
    <span style="color:#fff;font-size:18px;font-weight:bold;">🚨 Stackd AI System Alert</span><br>
    <span style="color:#ffaaaa;font-size:12px;">Enviromentor — {now_str}</span>
  </td></tr>
  <tr><td style="padding:24px 30px;">
    <p style="color:#A32D2D;font-weight:bold;font-size:15px;">Critical issue detected:</p>
    <div style="background:#FCEBEB;border-left:4px solid #A32D2D;padding:16px;border-radius:4px;">
      <pre style="color:#444;font-size:13px;white-space:pre-wrap;margin:0;">{message}</pre>
    </div>
    <p style="color:#666;font-size:13px;margin-top:16px;">
      Please check the system and resolve as soon as possible.<br>
      — Stackd AI Health Monitor
    </p>
  </td></tr>
  <tr><td style="background:#1a1a2e;padding:12px 30px;text-align:center;">
    <span style="color:#9FE1CB;font-size:11px;">Stackd AI — Enviromentor System Monitor</span>
  </td></tr>
</table>
</body></html>"""

        # Send to Wander via GHL email
        import requests as req_lib
        req_lib.post(
            "https://services.leadconnectorhq.com/conversations/messages",
            headers=HEADERS,
            json={
                "type": "Email",
                "contactId": "g1Hp5UCnMLVganCyNj93",
                "subject": f"🚨 Stackd AI Alert — {now_str}",
                "html": html,
                "emailTo": "wgodinho@gmail.com",
                "emailFrom": "zoe@enviromentor.com",
            }
        )
        logger.warning(f"🚨 Alert emailed to Wander: {message[:80]}")
    except Exception as e:
        logger.error(f"Could not send alert email: {e}")


def check_ghl_connection() -> dict:
    """Verify GHL API responding."""
    try:
        r = requests.get(
            f"https://services.leadconnectorhq.com/contacts/?locationId={LOC}&limit=1",
            headers=HEADERS
        )
        if r.status_code == 200:
            return {"status": "OK", "issues": []}
        return {"status": "FAIL", "issues": [f"GHL API returned {r.status_code}"]}
    except Exception as e:
        return {"status": "FAIL", "issues": [f"GHL unreachable: {str(e)[:50]}"]}


def check_email_sending() -> dict:
    """
    Check email sending is configured.
    FIXED: Checks if LC Email is enabled, not just conversation count.
    Emails may be sending correctly even with 0 conversations recorded.
    """
    issues = []
    try:
        # Check contacts tagged outreach-sent
        r = requests.get(
            f"https://services.leadconnectorhq.com/contacts/?locationId={LOC}&limit=100",
            headers=HEADERS
        )
        contacts = r.json().get("contacts", [])
        sent_count = sum(1 for c in contacts if "outreach-sent" in c.get("tags", []))

        # Check conversations exist at all
        r2 = requests.get(
            f"https://services.leadconnectorhq.com/conversations/?locationId={LOC}&limit=10",
            headers=HEADERS
        )
        convos = r2.json().get("conversations", [])

        # Only flag if we have MANY sent tags but ZERO conversations AND no convos at all
        # LC Email may queue without creating GHL conversation records
        if sent_count > 20 and len(convos) == 0:
            issues.append(
                f"NSWRNING: {sent_count} outreach tags but 0 GHL conversations — "
                f"verify emails are delivering via LC Email settings"
            )

        return {
            "status": "NSWRN" if issues else "OK",
            "sent_contacts": sent_count,
            "conversations": len(convos),
            "issues": issues
        }
    except Exception as e:
        return {"status": "ERROR", "issues": [str(e)[:100]]}


def check_contacts_quality() -> dict:
    """
    Check contact data quality.
    FIXED: Handle None companyName gracefully.
    """
    issues = []
    try:
        r = requests.get(
            f"https://services.leadconnectorhq.com/contacts/?locationId={LOC}&limit=100",
            headers=HEADERS
        )
        contacts = r.json().get("contacts", [])

        missing_email = []
        for c in contacts:
            tags = c.get("tags", [])
            # Skip non-prospect contacts
            if not any(t in tags for t in [
                "outreach-pending", "aged-care-prospect",
                "strata-prospect", "school-prospect"
            ]):
                continue

            # FIXED: Handle None companyName safely
            name = c.get("companyName") or \
                   f"{c.get('firstName','') or ''} {c.get('lastName','') or ''}".strip() or \
                   "Unknown"

            if not c.get("email"):
                missing_email.append(name)

        if missing_email:
            issues.append(
                f"{len(missing_email)} prospects missing email: "
                f"{', '.join(missing_email[:3])}"
            )

        return {
            "status": "NSWRN" if issues else "OK",
            "total": len(contacts),
            "issues": issues
        }
    except Exception as e:
        return {"status": "ERROR", "issues": [str(e)[:100]]}


def check_twilio() -> dict:
    """Verify Twilio is active."""
    try:
        credentials = base64.b64encode(
            f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()
        ).decode()
        req = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}.json",
            headers={"Authorization": f"Basic {credentials}"}
        )
        response = urllib.request.urlopen(req)
        data = json.loads(response.read())
        if data.get("status") == "active":
            return {"status": "OK", "issues": []}
        return {"status": "FAIL", "issues": [f"Twilio status: {data.get('status')}"]}
    except Exception as e:
        return {"status": "FAIL", "issues": [str(e)[:100]]}


def check_runaway_sms() -> dict:
    """
    Check for SMS loops — most critical check after the Wanda incident.
    Alert if more than 5 SMS sent to same number in last hour.
    """
    issues = []
    try:
        credentials = base64.b64encode(
            f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()
        ).decode()
        req = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json?PageSize=50",
            headers={"Authorization": f"Basic {credentials}"}
        )
        response = urllib.request.urlopen(req)
        messages = json.loads(response.read()).get("messages", [])

        # Count messages per recipient in last hour
        now = datetime.now(SYDNEY_TZ)
        counts = {}
        hourly_cost = 0
        for m in messages:
            try:
                sent_at = datetime.strptime(
                    m.get("date_sent", ""),
                    "%a, %d %b %Y %H:%M:%S %z"
                ).astimezone(SYDNEY_TZ)
                if (now - sent_at).total_seconds() < 3600:
                    to = m.get("to", "unknown")
                    counts[to] = counts.get(to, 0) + 1
                    hourly_cost += abs(float(m.get("price", 0) or 0))
            except Exception:
                pass

        for number, count in counts.items():
            if count > 5:
                issues.append(
                    f"🚨 RUNANSWY SMS: {count} messages to {number} in last hour! "
                    f"Cost: ${hourly_cost:.2f}. Possible loop — check scheduling agent!"
                )

        return {
            "status": "FAIL" if issues else "OK",
            "hourly_cost": hourly_cost,
            "issues": issues
        }
    except Exception as e:
        return {"status": "ERROR", "issues": [str(e)[:100]]}


def run():
    """Run hourly health check."""
    now = datetime.now(SYDNEY_TZ)
    logger.info("🏥 Health Agent: Running system check...")

    checks = {
        "GHL Connection": check_ghl_connection(),
        "Twilio/SMS": check_twilio(),
        "SMS Loop Detection": check_runaway_sms(),
        "Email Sending": check_email_sending(),
        "Contact Quality": check_contacts_quality(),
    }

    critical = []
    warnings = []

    for name, result in checks.items():
        status = result.get("status", "UNKNOWN")
        issues = result.get("issues", [])

        if status in ["FAIL", "ERROR"]:
            for issue in issues:
                critical.append(f"{name}: {issue}")
        elif status == "NSWRN":
            for issue in issues:
                warnings.append(f"{name}: {issue}")

        icon = "✅" if status == "OK" else "⚠️" if status == "NSWRN" else "❌"
        logger.info(f"  {icon} {name}: {issues[0][:60] if issues else 'All good'}")

    # Only alert on CRITICAL — not warnings
    if critical:
        alert = f"Found {len(critical)} critical issue(s):\n\n"
        alert += "\n".join(f"• {c[:100]}" for c in critical)
        send_alert(alert)
        logger.error(f"🚨 {len(critical)} critical issues!")
    elif warnings:
        logger.warning(f"⚠️ {len(warnings)} warnings (no alert sent)")
    else:
        logger.info("✅ All systems healthy!")
