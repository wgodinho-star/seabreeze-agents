"""
Scheduling Agent — appointment reminders via SMS.
FIXED: Checks reminder-sent tag before firing.
Never sends the same reminder twice.
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

KEY = os.getenv("GHL_SEABREEZE_KEY")
LOC = os.getenv("GHL_SEABREEZE_LOCATION_ID")
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Version": "2021-07-28",
    "Content-Type": "application/json"
}

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_AU_NUMBER", "+61480891085")


def send_sms(to_number: str, message: str) -> bool:
    """Send SMS via Twilio."""
    try:
        credentials = base64.b64encode(
            f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()
        ).decode()
        data = urllib.parse.urlencode({
            "Body": message,
            "From": TWILIO_NUMBER,
            "To": to_number
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
        return True
    except Exception as e:
        logger.error(f"SMS failed: {e}")
        return False


def mark_reminder_sent(contact_id: str, reminder_type: str):
    """Tag contact so reminder is NEVER sent again."""
    requests.put(
        f"https://services.leadconnectorhq.com/contacts/{contact_id}",
        headers=HEADERS,
        json={"tags": [f"{reminder_type}-sent"]}
    )


def get_upcoming_appointments() -> list:
    """Get appointments in next 25 hours that haven't been reminded yet."""
    try:
        now = datetime.now(PERTH_TZ)
        tomorrow = now + timedelta(hours=25)

        r = requests.get(
            f"https://services.leadconnectorhq.com/calendars/events",
            headers=HEADERS,
            params={
                "locationId": LOC,
                "startTime": int(now.timestamp() * 1000),
                "endTime": int(tomorrow.timestamp() * 1000)
            }
        )
        events = r.json().get("events", [])
        logger.info(f"📅 Found {len(events)} upcoming appointments")
        return events
    except Exception as e:
        logger.error(f"Error fetching appointments: {e}")
        return []


def run():
    """Check appointments and send reminders — ONCE per appointment only."""
    now = datetime.now(PERTH_TZ)

    # Only run between 8am and 8pm Perth time
    if not (8 <= now.hour < 20):
        return

    appointments = get_upcoming_appointments()

    for appt in appointments:
        contact_id = appt.get("contactId")
        if not contact_id:
            continue

        # ── CRITICAL FIX: Check if reminder already sent ──────────
        contact_r = requests.get(
            f"https://services.leadconnectorhq.com/contacts/{contact_id}",
            headers=HEADERS
        )
        contact = contact_r.json().get("contact", {})
        tags = contact.get("tags", [])

        appt_id = appt.get("id", contact_id)
        reminder_tag = f"reminder-sent-{appt_id}"

        if reminder_tag in tags:
            logger.info(f"⏭️  Reminder already sent for {contact.get('firstName')} — skipping")
            continue
        # ──────────────────────────────────────────────────────────

        phone = contact.get("phone", "")
        name = contact.get("firstName", "there")
        start_time = appt.get("startTime", "")

        if not phone:
            continue

        # Format time
        try:
            appt_dt = datetime.fromtimestamp(
                int(start_time) / 1000, tz=PERTH_TZ
            )
            time_str = appt_dt.strftime("%A %d %B at %-I:%M%p").replace("AM","am").replace("PM","pm")
        except Exception:
            time_str = "tomorrow"

        message = (
            f"Hi {name}! 🌿 Just a friendly reminder from Sea Breeze Maintenance — "
            f"Francisco is visiting {time_str} for your service. "
            f"Need to reschedule? Call Zoe on 0480 891 085. See you soon!"
        )

        if send_sms(phone, message):
            # ── Mark as sent IMMEDIATELY after sending ────────────
            mark_reminder_sent(contact_id, f"reminder-sent-{appt_id}")
            logger.info(f"✅ Reminder sent to {name} — tagged, will not fire again")
        else:
            logger.error(f"❌ Failed to send reminder to {name}")
