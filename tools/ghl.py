"""
GoHighLevel API wrapper for Seabreeze Maintenance
All API calls go through this module.
"""
import os
import requests
from typing import Optional

BASE_URL = "https://services.leadconnectorhq.com"
HEADERS = {
    "Authorization": f"Bearer {os.getenv('GHL_SEABREEZE_KEY')}",
    "Version": "2021-07-28",
    "Content-Type": "application/json"
}
LOCATION_ID = os.getenv("GHL_SEABREEZE_LOCATION_ID")
PIPELINE_ID = os.getenv("GHL_SEABREEZE_PIPELINE_ID")


# ── CONTACTS ───────────────────────────────────────────────────

def get_contacts(limit: int = 20) -> list:
    """Fetch recent contacts/leads from GHL."""
    r = requests.get(
        f"{BASE_URL}/contacts/",
        headers=HEADERS,
        params={"locationId": LOCATION_ID, "limit": limit}
    )
    return r.json().get("contacts", [])


def create_contact(first_name: str, last_name: str, phone: str,
                   email: str = None, suburb: str = None,
                   service_type: str = None, source: str = "website") -> dict:
    """Create a new lead contact in GHL."""
    payload = {
        "locationId": LOCATION_ID,
        "firstName": first_name,
        "lastName": last_name,
        "phone": phone,
        "source": source,
        "type": "lead",
        "tags": ["new-lead"]
    }
    if email:
        payload["email"] = email
    if suburb:
        payload["city"] = suburb
    if service_type:
        payload["tags"].append(service_type.lower().replace(" ", "-"))

    r = requests.post(f"{BASE_URL}/contacts/", headers=HEADERS, json=payload)
    return r.json().get("contact", {})


def update_contact_tags(contact_id: str, tags: list) -> dict:
    """Add tags to a contact."""
    r = requests.put(
        f"{BASE_URL}/contacts/{contact_id}",
        headers=HEADERS,
        json={"tags": tags}
    )
    return r.json()


# ── OPPORTUNITIES (PIPELINE) ────────────────────────────────────

def get_pipeline_stages() -> list:
    """Get all stages in the Seabreeze pipeline."""
    r = requests.get(
        f"{BASE_URL}/opportunities/pipelines",
        headers=HEADERS,
        params={"locationId": LOCATION_ID}
    )
    pipelines = r.json().get("pipelines", [])
    for p in pipelines:
        if p["id"] == PIPELINE_ID:
            return p.get("stages", [])
    return []


def create_opportunity(contact_id: str, title: str, stage_id: str,
                       value: float = 0, status: str = "open") -> dict:
    """Create a new opportunity in the pipeline."""
    r = requests.post(
        f"{BASE_URL}/opportunities/",
        headers=HEADERS,
        json={
            "locationId": LOCATION_ID,
            "pipelineId": PIPELINE_ID,
            "pipelineStageId": stage_id,
            "contactId": contact_id,
            "name": title,
            "monetaryValue": value,
            "status": status
        }
    )
    return r.json().get("opportunity", {})


def move_opportunity(opportunity_id: str, stage_id: str) -> dict:
    """Move an opportunity to a new pipeline stage."""
    r = requests.put(
        f"{BASE_URL}/opportunities/{opportunity_id}",
        headers=HEADERS,
        json={"pipelineStageId": stage_id}
    )
    return r.json()


def get_opportunities(stage_id: str = None) -> list:
    """Get all opportunities, optionally filtered by stage."""
    params = {"location_id": LOCATION_ID, "pipeline_id": PIPELINE_ID}
    if stage_id:
        params["pipeline_stage_id"] = stage_id
    r = requests.get(f"{BASE_URL}/opportunities/search", headers=HEADERS, params=params)
    return r.json().get("opportunities", [])


# ── NOTES ──────────────────────────────────────────────────────

def add_note(contact_id: str, note: str) -> dict:
    """Add a note to a contact record."""
    r = requests.post(
        f"{BASE_URL}/contacts/{contact_id}/notes",
        headers=HEADERS,
        json={"body": note}
    )
    return r.json()


# ── CONVERSATIONS / SMS ─────────────────────────────────────────

def send_sms(contact_id: str, message: str) -> dict:
    """Send an SMS to a contact via GHL."""
    r = requests.post(
        f"{BASE_URL}/conversations/messages",
        headers=HEADERS,
        json={
            "type": "SMS",
            "contactId": contact_id,
            "message": message
        }
    )
    return r.json()


def get_conversations(contact_id: str) -> list:
    """Get conversation history for a contact."""
    r = requests.get(
        f"{BASE_URL}/conversations/search",
        headers=HEADERS,
        params={"locationId": LOCATION_ID, "contactId": contact_id}
    )
    return r.json().get("conversations", [])


# ── CALENDAR ───────────────────────────────────────────────────

def get_appointments(start_time: str, end_time: str) -> list:
    """Get appointments within a date range (ISO format)."""
    r = requests.get(
        f"{BASE_URL}/calendars/events",
        headers=HEADERS,
        params={
            "locationId": LOCATION_ID,
            "startTime": start_time,
            "endTime": end_time
        }
    )
    return r.json().get("events", [])


def create_appointment(contact_id: str, calendar_id: str, start_time: str,
                        end_time: str, title: str = None) -> dict:
    """Book a calendar appointment for a contact."""
    payload = {
        "locationId": LOCATION_ID,
        "calendarId": calendar_id,
        "contactId": contact_id,
        "startTime": start_time,
        "endTime": end_time,
        "status": "booked"
    }
    if title:
        payload["title"] = title
    resp = requests.post(
        f"{BASE_URL}/calendars/events/appointments",
        headers=HEADERS,
        json=payload
    )
    return resp.json()


def create_or_get_contact(first_name: str, last_name: str, phone: str,
                           email: str = None, suburb: str = None,
                           service_type: str = None) -> dict:
    """Find existing contact by phone or create new one."""
    search = requests.get(
        f"{BASE_URL}/contacts/search/duplicate",
        headers=HEADERS,
        params={"locationId": LOCATION_ID, "phone": phone}
    )
    existing = search.json().get("contact")
    if existing:
        return existing
    return create_contact(first_name, last_name, phone, email, suburb, service_type, source="zoe-call")
