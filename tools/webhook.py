"""
Vapi webhook handler — processes tool calls from Zoe
Routes: /vapi/book-appointment, /vapi/notify-francisco, /health
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from tools.ghl import create_or_get_contact, create_appointment, add_note, send_sms
from tools.twilio_sms import send_sms as twilio_sms

logger = logging.getLogger(__name__)

CALENDAR_QUOTE = "wEFmjLtxfMpqLddEGclq"
CALENDAR_VIDEO = "nw5pHWDkDAhZNwUILPcQ"
FRANCISCO_CONTACT = "lcR0DMJ4JufVyrMAbuLL"
FRANCISCO_PHONE = "+61404590230"


def register_routes(app: FastAPI):
    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "Stackd AI — Sea Breeze Agents"}

    @app.post("/vapi/book-appointment")
    async def book_appointment(request: Request):
        body = await request.json()
        args = body.get("message", {}).get("toolCallList", [{}])[0].get("function", {}).get("arguments", {})
        if isinstance(args, str):
            import json as _json
            args = _json.loads(args)

        first_name = args.get("firstName", "")
        last_name = args.get("lastName", "")
        phone = args.get("phone", "")
        email = args.get("email", "")
        suburb = args.get("suburb", "")
        appointment_type = args.get("appointmentType", "quote")  # "quote" or "video"
        preferred_date = args.get("preferredDate", "")
        preferred_time = args.get("preferredTime", "")
        notes = args.get("notes", "")

        try:
            contact = create_or_get_contact(first_name, last_name, phone, email, suburb, appointment_type)
            contact_id = contact.get("id", "")

            if contact_id:
                add_note(contact_id, f"Booked via Zoe call. Type: {appointment_type}. Preferred: {preferred_date} {preferred_time}. Notes: {notes}")

            calendar_id = CALENDAR_VIDEO if appointment_type == "video" else CALENDAR_QUOTE
            result_msg = ""

            if appointment_type == "video":
                # Don't auto-book video — notify Francisco to confirm
                francisco_msg = (
                    f"🎥 VIDEO CONSULTATION REQUEST\n"
                    f"Name: {first_name} {last_name}\n"
                    f"Phone: {phone}\n"
                    f"Email: {email}\n"
                    f"Suburb: {suburb}\n"
                    f"Preferred: {preferred_date} {preferred_time}\n"
                    f"Notes: {notes}\n"
                    f"Please confirm & send Google Meet link."
                )
                try:
                    twilio_sms(FRANCISCO_PHONE, francisco_msg)
                except Exception as e:
                    logger.warning(f"SMS to Francisco failed: {e}")
                result_msg = "Video consultation request received. Francisco has been notified and will confirm within 2 hours with a meeting link."
            else:
                result_msg = f"Quote inspection noted. {first_name}, Francisco will confirm your appointment shortly."

            tool_call_id = body.get("message", {}).get("toolCallList", [{}])[0].get("id", "")
            return JSONResponse({
                "results": [{
                    "toolCallId": tool_call_id,
                    "result": result_msg
                }]
            })

        except Exception as e:
            logger.error(f"book_appointment error: {e}")
            tool_call_id = body.get("message", {}).get("toolCallList", [{}])[0].get("id", "")
            return JSONResponse({
                "results": [{
                    "toolCallId": tool_call_id,
                    "result": "I've noted your details and Francisco will be in touch shortly to confirm."
                }]
            })
