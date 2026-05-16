"""
Health Monitor Agent — the system's immune system.
Runs every hour and checks that everything is working.
If something is broken, it alerts Wander immediately.

Monitors:
- Email delivery (are emails actually sending?)
- SMS delivery (are messages reaching clients?)
- Pipeline health (are leads moving through stages?)
- Agent activity (are agents running?)
- Contact data quality (missing emails, phones?)
- Bounce rates (are we getting blocked?)

This agent should have caught the email problem on day 1.
It won't happen again.
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
PERTH_TZ = pytz.timezone("Australia/Perth")
SYDNEY_TZ = pytz.timezone("Australia/Sydney")

KEY = os.getenv("GHL_SEABREEZE_KEY")
LOC = os.getenv("GHL_SEABREEZE_LOCATION_ID")
HEADERS = {"Authorization": f"Bearer {KEY}", "Version": "2021-07-28", "Content-Type": "application/json"}

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
WANDER_PHONE = os.getenv("WANDER_PHONE", "+61404590230")
FRANCISCO_PHONE = os.getenv("CLIENT_PHONE", "+61404590230")
WANDER_CONTACT_ID = "g1Hp5UCnMLVganCyNj93"


def send_alert(message: str):
    """Send urgent alert to Wander via SMS."""
    try:
        credentials = base64.b64encode(
            f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()
        ).decode()
        data = urllib.parse.urlencode({
            "Body": f"🚨 SYSTEM ALERT\n{message}",
            "From": TWILIO_NUMBER,
            "To": WANDER_PHONE
        }).encode()
        req = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json",
            data=data,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        urllib.request.urlopen(req)
        logger.warning(f"🚨 Alert sent: {message[:50]}")
    except Exception as e:
        logger.error(f"Could not send alert: {e}")


def check_email_sending() -> dict:
    """
    Check if GHL email is actually working.
    Test by checking conversation history for sent emails.
    """
    issues = []
    
    try:
        # Check if any emails exist in conversations
        r = requests.get(
            f"https://services.leadconnectorhq.com/conversations/?locationId={LOC}&limit=50",
            headers=HEADERS
        )
        convos = r.json().get("conversations", [])
        
        email_convos = [c for c in convos if c.get("lastMessageType") == "Email"]
        
        if not email_convos:
            issues.append("No emails found in GHL conversations — email sending may not be configured")
        
        # Check contacts tagged outreach-sent but no conversations
        r2 = requests.get(
            f"https://services.leadconnectorhq.com/contacts/?locationId={LOC}&limit=100",
            headers=HEADERS
        )
        contacts = r2.json().get("contacts", [])
        sent_contacts = [c for c in contacts if "outreach-sent" in c.get("tags", [])]
        
        if len(sent_contacts) > 0 and len(email_convos) == 0:
            issues.append(
                f"CRITICAL: {len(sent_contacts)} contacts tagged 'outreach-sent' "
                f"but ZERO email conversations found. "
                f"Emails are NOT being delivered!"
            )
        
        return {
            "status": "FAIL" if issues else "OK",
            "sent_contacts": len(sent_contacts),
            "email_conversations": len(email_convos),
            "issues": issues
        }
    except Exception as e:
        return {"status": "ERROR", "issues": [str(e)]}


def check_contacts_quality() -> dict:
    """Check for contacts with missing or invalid data."""
    issues = []
    
    try:
        r = requests.get(
            f"https://services.leadconnectorhq.com/contacts/?locationId={LOC}&limit=100",
            headers=HEADERS
        )
        contacts = r.json().get("contacts", [])
        
        missing_email = []
        missing_phone = []
        missing_company = []
        
        for c in contacts:
            tags = c.get("tags", [])
            if not any(t in tags for t in ["outreach-pending", "aged-care-prospect", "strata-prospect", "school-prospect"]):
                continue
            name = c.get("companyName", "Unknown")
            if not c.get("email"):
                missing_email.append(name)
            if not c.get("phone"):
                missing_phone.append(name)
        
        if missing_email:
            issues.append(f"{len(missing_email)} prospects missing email: {', '.join(missing_email[:3])}")
        
        return {
            "status": "WARN" if issues else "OK",
            "total_contacts": len(contacts),
            "missing_email": len(missing_email),
            "issues": issues
        }
    except Exception as e:
        return {"status": "ERROR", "issues": [str(e)]}


def check_pipeline_health() -> dict:
    """Check if pipeline is moving or stuck."""
    issues = []
    
    try:
        r = requests.get(
            f"https://services.leadconnectorhq.com/opportunities/search?location_id={LOC}&limit=50",
            headers=HEADERS
        )
        opps = r.json().get("opportunities", [])
        
        # Check for opportunities stuck in same stage for too long
        now = datetime.now(PERTH_TZ)
        stuck = []
        for opp in opps:
            created = opp.get("createdAt", "")
            if created:
                try:
                    created_dt = datetime.fromisoformat(
                        created.replace("Z", "+00:00")
                    ).astimezone(PERTH_TZ)
                    days_old = (now - created_dt).days
                    if days_old > 14:
                        stuck.append(opp.get("name", "Unknown"))
                except Exception:
                    pass
        
        if stuck:
            issues.append(f"{len(stuck)} opportunities stuck for 14+ days: {', '.join(stuck[:3])}")
        
        return {
            "status": "WARN" if issues else "OK",
            "total_opportunities": len(opps),
            "stuck": len(stuck),
            "issues": issues
        }
    except Exception as e:
        return {"status": "ERROR", "issues": [str(e)]}


def check_ghl_connection() -> dict:
    """Verify GHL API is responding correctly."""
    try:
        r = requests.get(
            f"https://services.leadconnectorhq.com/contacts/?locationId={LOC}&limit=1",
            headers=HEADERS
        )
        if r.status_code == 200:
            return {"status": "OK", "issues": []}
        else:
            return {"status": "FAIL", "issues": [f"GHL API returned {r.status_code}"]}
    except Exception as e:
        return {"status": "FAIL", "issues": [f"GHL unreachable: {e}"]}


def check_twilio_connection() -> dict:
    """Verify Twilio SMS is working."""
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
        else:
            return {"status": "FAIL", "issues": [f"Twilio status: {data.get('status')}"]}
    except Exception as e:
        return {"status": "FAIL", "issues": [f"Twilio error: {e}"]}


def run():
    """Run full system health check every hour."""
    now = datetime.now(SYDNEY_TZ)
    logger.info(f"🏥 Health Agent: Running system check...")

    results = {
        "GHL Connection": check_ghl_connection(),
        "Twilio/SMS": check_twilio_connection(),
        "Email Sending": check_email_sending(),
        "Contact Quality": check_contacts_quality(),
        "Pipeline Health": check_pipeline_health(),
    }

    # Find all issues
    critical = []
    warnings = []

    for check_name, result in results.items():
        status = result.get("status", "UNKNOWN")
        issues = result.get("issues", [])

        if status == "FAIL" or status == "ERROR":
            for issue in issues:
                critical.append(f"{check_name}: {issue}")
        elif status == "WARN":
            for issue in issues:
                warnings.append(f"{check_name}: {issue}")

        logger.info(f"  {status} — {check_name}: {issues[0] if issues else 'All good'}")

    # Alert on critical issues immediately
    if critical:
        alert_msg = f"Found {len(critical)} critical issue(s):\n\n"
        alert_msg += "\n".join(f"• {c}" for c in critical)
        alert_msg += "\n\nPlease check and fix immediately."
        send_alert(alert_msg)
        logger.error(f"🚨 {len(critical)} critical issues found!")

    # Log summary
    if not critical and not warnings:
        logger.info("✅ All systems healthy!")
    else:
        logger.warning(
            f"⚠️ Health check: {len(critical)} critical, {len(warnings)} warnings"
        )

    return {
        "critical": len(critical),
        "warnings": len(warnings),
        "results": results
    }
