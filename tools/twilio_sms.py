"""
Twilio SMS tool — direct SMS sending for all Seabreeze agents.
More reliable than GHL SMS for automated messages.
"""
import os
from twilio.rest import Client

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+61876490100")

_client = None

def get_client():
    global _client
    if not _client:
        _client = Client(ACCOUNT_SID, AUTH_TOKEN)
    return _client


def send_sms(to_number: str, message: str) -> dict:
    """Send an SMS via Twilio."""
    try:
        client = get_client()
        msg = client.messages.create(
            body=message,
            from_=TWILIO_NUMBER,
            to=to_number
        )
        return {
            "success": True,
            "sid": msg.sid,
            "status": msg.status,
            "to": to_number
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "to": to_number
        }


def send_sms_to_francisco(message: str) -> dict:
    """Send a notification SMS directly to Francisco."""
    return send_sms(
        to_number=os.getenv("CLIENT_PHONE", "+61404590230"),
        message=message
    )


def get_incoming_messages(limit: int = 20) -> list:
    """Get recent incoming SMS messages."""
    try:
        client = get_client()
        messages = client.messages.list(
            to=TWILIO_NUMBER,
            limit=limit
        )
        return [
            {
                "sid": m.sid,
                "from": m.from_,
                "body": m.body,
                "status": m.status,
                "date_sent": str(m.date_sent)
            }
            for m in messages
        ]
    except Exception as e:
        return []
