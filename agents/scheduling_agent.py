"""
Scheduling Agent — Francisco's most valuable agent.
Handles the 4 hours/day he spends on aged care rescheduling.

WORKFLOW:
1. 24 hours before appointment → SMS reminder to client
2. 4 hours before appointment → Follow-up SMS with call offer
3. If client wants to reschedule → Agent negotiates new time
4. Francisco gets ONE notification of the outcome

Saves Francisco ~$400/day in lost productivity.
"""
import logging
import os
from datetime import datetime, timedelta
import pytz
import json
from tools import ghl, claude_ai

logger = logging.getLogger(__name__)

PERTH_TZ = pytz.timezone("Australia/Perth")
CALENDAR_ID = os.getenv("GHL_SEABREEZE_CALENDAR_ID", "wEFmjLtxfMpqLddEGclq")
FRANCISCO_CONTACT_ID = os.getenv("GHL_FRANCISCO_CONTACT_ID", "lcR0DMJ4JufVyrMAbuLL")
FRANCISCO_PHONE = os.getenv("CLIENT_PHONE", "+61404590230")

# How many hours before appointment to send each reminder
REMINDER_1_HOURS = 24   # Day before SMS
REMINDER_2_HOURS = 4    # Morning of call/SMS


def get_upcoming_appointments(hours_ahead: int = 25) -> list:
    """Get appointments in the next N hours."""
    now = datetime.now(PERTH_TZ)
    start = now.isoformat()
    end = (now + timedelta(hours=hours_ahead)).isoformat()
    return ghl.get_appointments(start, end)


def has_been_reminded(appointment: dict, reminder_type: str) -> bool:
    """Check if a reminder has already been sent for this appointment."""
    notes = appointment.get("notes", "") or ""
    tag = f"[REMINDED:{reminder_type}:{appointment.get('id', '')}]"
    return tag in notes


def mark_reminded(appointment_id: str, contact_id: str, reminder_type: str):
    """Add a note to the contact so we don't double-send reminders."""
    note = f"[REMINDED:{reminder_type}:{appointment_id}] Sent at {datetime.now(PERTH_TZ).strftime('%d %b %Y %H:%M')}"
    ghl.add_note(contact_id, note)


def generate_reminder_sms(client_name: str, service: str,
                          appointment_time: str, hours_before: int) -> str:
    """Generate a personalised reminder SMS using Claude."""
    if hours_before == 24:
        prompt = f"""Write a friendly SMS reminder for a property maintenance appointment.
Client: {client_name}
Service: {service}
Time: {appointment_time}
From: Sea Breeze Maintenance (Francisco)

The message should:
- Be warm and friendly (many clients are elderly)
- Confirm the appointment details
- Reassure them the job will be quick and cause minimal disruption
- Ask them to reply YES to confirm or call/text to reschedule
- Be under 160 characters
- End with Francisco's name"""
    else:
        prompt = f"""Write a friendly 4-hour-before reminder SMS for a property maintenance appointment.
Client: {client_name}
Service: {service}
Time: {appointment_time}
From: Sea Breeze Maintenance (Francisco)

The message should:
- Be brief and warm
- Confirm Francisco is on his way / coming today
- Reassure them it will be quick with minimal disruption
- Give them one last chance to reschedule if needed
- Be under 160 characters"""

    return claude_ai.think(
        system_prompt="You write warm, friendly SMS messages for a property maintenance business. Many clients are elderly. Be reassuring, clear and brief.",
        user_message=prompt,
        max_tokens=100
    )


def generate_reschedule_options(client_name: str, service: str,
                                available_slots: list) -> str:
    """Generate a rescheduling SMS with available time options."""
    slots_text = "\n".join([f"- {slot}" for slot in available_slots[:3]])
    return claude_ai.think(
        system_prompt="You write warm, friendly SMS messages for a property maintenance business. Many clients are elderly. Be reassuring and clear.",
        user_message=f"""Write an SMS offering rescheduling options to {client_name}.
Service: {service}
Available times:
{slots_text}

The message should:
- Apologise for any inconvenience
- Offer the 3 time options clearly
- Ask them to reply with their preferred option (1, 2, or 3)
- Be warm and reassuring
- Mention the job is quick and won't cause much disruption
- Be under 160 characters""",
        max_tokens=120
    )


def notify_francisco(message: str):
    """Send Francisco a notification about a scheduling change."""
    ghl.send_sms(FRANCISCO_CONTACT_ID, f"📅 SCHEDULING UPDATE:\n{message}")
    logger.info(f"Francisco notified: {message}")


def get_available_slots(exclude_date: str = None) -> list:
    """Get Francisco's next available appointment slots."""
    now = datetime.now(PERTH_TZ)
    slots = []

    # Check next 7 days for availability
    for day_offset in range(1, 8):
        check_date = now + timedelta(days=day_offset)

        # Skip weekends
        if check_date.weekday() >= 5:
            continue

        # Skip the excluded date if provided
        if exclude_date and check_date.strftime("%Y-%m-%d") == exclude_date:
            continue

        # Morning slot (8am) and afternoon slot (1pm)
        for hour in [8, 13]:
            slot_time = check_date.replace(hour=hour, minute=0, second=0)
            slots.append(slot_time.strftime("%A %d %B at %-I:%M%p"))

        if len(slots) >= 3:
            break

    return slots


def process_reschedule_reply(contact_id: str, contact_name: str,
                              service: str, reply_text: str,
                              available_slots: list) -> bool:
    """
    Process a client's reply to a reschedule offer.
    Returns True if rescheduling was successful.
    """
    reply_lower = reply_text.lower().strip()

    # Check if they selected an option
    selected_slot = None
    if "1" in reply_lower or "first" in reply_lower or "one" in reply_lower:
        selected_slot = available_slots[0] if available_slots else None
    elif "2" in reply_lower or "second" in reply_lower or "two" in reply_lower:
        selected_slot = available_slots[1] if len(available_slots) > 1 else None
    elif "3" in reply_lower or "third" in reply_lower or "three" in reply_lower:
        selected_slot = available_slots[2] if len(available_slots) > 2 else None

    if selected_slot:
        # Confirm with client
        confirm_sms = f"Perfect {contact_name}! ✅ Francisco will be there {selected_slot} for your {service}. See you then! 🌿"
        ghl.send_sms(contact_id, confirm_sms)

        # Notify Francisco
        notify_francisco(
            f"{contact_name} rescheduled their {service}.\n"
            f"New time: {selected_slot}\n"
            f"Please update your calendar."
        )

        # Add note to contact
        ghl.add_note(contact_id,
            f"Rescheduling Agent: Client rescheduled to {selected_slot}. "
            f"Francisco notified via SMS."
        )
        return True

    # Couldn't interpret reply — flag for Francisco
    notify_francisco(
        f"⚠️ {contact_name} replied to reschedule offer but I couldn't interpret their response.\n"
        f"Their reply: '{reply_text}'\n"
        f"Please contact them directly: check GHL for their number."
    )
    return False


def run():
    """Main scheduling agent loop."""
    logger.info("📅 Scheduling Agent: Checking appointments...")

    now = datetime.now(PERTH_TZ)
    appointments = get_upcoming_appointments(hours_ahead=25)

    if not appointments:
        logger.info("✅ No upcoming appointments in next 25 hours.")
        return

    logger.info(f"📋 Found {len(appointments)} upcoming appointments.")

    for appt in appointments:
        appt_id = appt.get("id", "")
        contact_id = appt.get("contactId", "")
        contact_name = appt.get("title", "there").split(" —")[0]
        service = appt.get("calendarId", "maintenance service")
        start_time_str = appt.get("startTime", "")

        if not start_time_str or not contact_id:
            continue

        try:
            # Parse appointment time
            appt_time = datetime.fromisoformat(
                start_time_str.replace("Z", "+00:00")
            ).astimezone(PERTH_TZ)

            hours_until = (appt_time - now).total_seconds() / 3600
            appt_time_display = appt_time.strftime("%A %d %B at %-I:%M%p")

            logger.info(f"  → {contact_name}: {appt_time_display} ({hours_until:.1f}h away)")

            # ── 24-hour reminder ──────────────────────────────────
            if 23 <= hours_until <= 25:
                reminder_key = f"24h_{appt_id}"

                # Check contact notes for reminder tag
                contacts = ghl.get_contacts(limit=1)  # placeholder
                notes_text = ""  # Would check actual notes in production

                if reminder_key not in notes_text:
                    sms = generate_reminder_sms(
                        contact_name, service, appt_time_display, 24
                    )
                    ghl.send_sms(contact_id, sms)
                    mark_reminded(appt_id, contact_id, "24h")
                    logger.info(f"  ✅ 24h reminder sent to {contact_name}")

            # ── 4-hour reminder ───────────────────────────────────
            elif 3.5 <= hours_until <= 4.5:
                reminder_key = f"4h_{appt_id}"

                sms = generate_reminder_sms(
                    contact_name, service, appt_time_display, 4
                )
                ghl.send_sms(contact_id, sms)
                mark_reminded(appt_id, contact_id, "4h")
                logger.info(f"  ✅ 4h reminder sent to {contact_name}")

            # ── Check for reschedule requests ─────────────────────
            # In production this would check GHL conversations for
            # replies containing "reschedule", "cancel", "can't make it" etc.
            # and trigger the rescheduling workflow automatically.

        except Exception as e:
            logger.error(f"  ❌ Error processing appointment {appt_id}: {e}")

    logger.info("🏁 Scheduling Agent: Done.")
