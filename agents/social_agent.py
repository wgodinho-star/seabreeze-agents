"""
Social Media Agent — auto-generates weekly content for Sea Breeze.

HOW IT WORKS:
1. Francisco uploads photos to GHL Media Storage (via his dashboard)
2. Every Monday this agent checks for new unposted photos
3. It reads the filename to understand what the photo shows
4. Claude writes a personalised caption matching the photo
5. Post is scheduled via GHL Social Planner (Facebook + Instagram)
6. Photo is tagged as "posted" so it's not used again

Francisco's job: upload photos to GHL Media Storage → everything else is automatic.
"""
import logging
import os
import requests
from datetime import datetime, timedelta
import pytz
from tools import claude_ai

logger = logging.getLogger(__name__)
PERTH_TZ = pytz.timezone("Australia/Perth")

KEY = os.getenv("GHL_SEABREEZE_KEY")
LOC = os.getenv("GHL_SEABREEZE_LOCATION_ID")
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Version": "2021-07-28",
    "Content-Type": "application/json"
}

FRANCISCO_CONTACT_ID = os.getenv("GHL_FRANCISCO_CONTACT_ID")
BUSINESS_NAME = "Sea Breeze Maintenance"
WEBSITE = "seabreezemaintenance.com.au"

HASHTAG_MAP = {
    "garden":    "#GardenMaintenance #GroundsMaintenance #PerthMaintenance #PropertySafety",
    "gutter":    "#GutterCleaning #PreventiveWorks #WaterDamage #HomeMaintenancePerth",
    "pressure":  "#PressureWashing #PropertyClean #DrivewayClean #PerthCleaning",
    "antislip":  "#AntiSlip #FallsPrevention #AgedCareSafety #PropertySafety",
    "before":    "#BeforeAndAfter #Transformation #PropertyMaintenance #Perth",
    "after":     "#BeforeAndAfter #Transformation #PropertyMaintenance #Perth",
    "team":      "#SeaBreezeTeam #LocalBusiness #PerthTrades #PropertyMaintenance",
    "aged":      "#AgedCare #AgedCareSafety #PropertyMaintenance #WesternAustralia",
    "strata":    "#StrataManagement #BodyCorporate #PropertyManagement #Perth",
    "default":   "#SeaBreezeMaintenance #PropertySafety #WesternAustralia #Perth",
}

BASE_HASHTAGS = "#SeaBreezeMaintenance #PerthMaintenance #SouthWestWA"


def get_hashtags(filename: str) -> str:
    """Pick relevant hashtags based on filename keywords."""
    fname = filename.lower()
    for keyword, tags in HASHTAG_MAP.items():
        if keyword in fname:
            return f"{tags} {BASE_HASHTAGS}"
    return f"{HASHTAG_MAP['default']} {BASE_HASHTAGS}"


def get_unposted_photos() -> list:
    """Fetch photos from GHL Media Storage that haven't been posted yet."""
    try:
        r = requests.get(
            f"https://services.leadconnectorhq.com/medias/files",
            headers=HEADERS,
            params={
                "locationId": LOC,
                "type": "image",
                "limit": 50
            }
        )
        all_files = r.json().get("files", [])

        # Filter out already-posted photos (tagged with "social-posted")
        unposted = [
            f for f in all_files
            if "social-posted" not in f.get("name", "")
            and not f.get("name", "").startswith("POSTED_")
        ]

        logger.info(f"📸 Found {len(all_files)} photos, {len(unposted)} unposted")
        return unposted

    except Exception as e:
        logger.error(f"❌ Error fetching GHL media: {e}")
        return []


def generate_caption(filename: str, url: str) -> str:
    """Generate a social media caption using Claude based on the filename."""

    # Clean filename for context
    clean_name = filename.replace("-", " ").replace("_", " ").replace(".jpg", "").replace(".png", "").replace(".jpeg", "")

    prompt = f"""Write a Facebook and Instagram post for Sea Breeze Maintenance.

The photo shows: {clean_name}

Sea Breeze Maintenance is a professional property safety and maintenance team 
serving Perth metro and South West WA (Dunsborough, Busselton, Margaret River).

Services: garden & grounds maintenance, preventive gutter works, 
pressure washing, anti-slip surface installation.

Target audience: aged care facility managers, strata property managers, homeowners.

Requirements:
- 3-5 sentences max
- Warm, professional, locally-focused tone
- Mention the relevant service naturally
- End with a soft call to action (free quote or inspection)
- DO NOT include hashtags (added separately)
- Use line breaks for readability

Write ONLY the caption text, nothing else."""

    return claude_ai.think(
        system_prompt="""You write engaging social media captions for Sea Breeze Maintenance, 
a property safety team in Perth and South West WA. 
Warm, professional, safety-focused, community-minded tone.
Never use corporate jargon. Write like a trusted local business.""",
        user_message=prompt,
        max_tokens=250
    )


def mark_as_posted(file_id: str, filename: str):
    """Rename the file in GHL to mark it as posted."""
    try:
        requests.put(
            f"https://services.leadconnectorhq.com/medias/files/{file_id}",
            headers=HEADERS,
            json={"name": f"POSTED_{filename}"}
        )
        logger.info(f"✅ Marked as posted: {filename}")
    except Exception as e:
        logger.error(f"❌ Could not mark as posted: {e}")


def schedule_post(caption: str, image_url: str, scheduled_time: str) -> bool:
    """Schedule a post via GHL Social Planner."""
    try:
        r = requests.post(
            f"https://services.leadconnectorhq.com/social-media-posting/{LOC}/post",
            headers=HEADERS,
            json={
                "locationId": LOC,
                "type": "post",
                "summary": caption,
                "media": [{"url": image_url, "type": "image"}],
                "scheduleDate": scheduled_time,
                "status": "scheduled"
            }
        )
        return r.status_code in [200, 201]
    except Exception:
        return False


def save_caption_as_note(caption: str, filename: str, scheduled_for: str):
    """Fallback: save caption to GHL note if Social Planner not connected."""
    note = (
        f"📱 SOCIAL MEDIA POST READY\n"
        f"Photo: {filename}\n"
        f"Schedule: {scheduled_for}\n"
        f"{'─'*40}\n\n"
        f"{caption}\n\n"
        f"{'─'*40}\n"
        f"ACTION: Post this to Facebook + Instagram\n"
        f"Connect GHL Social Planner to automate posting."
    )
    requests.post(
        f"https://services.leadconnectorhq.com/contacts/{FRANCISCO_CONTACT_ID}/notes",
        headers=HEADERS,
        json={"body": note}
    )
    logger.info(f"📝 Caption saved to GHL notes for manual posting")


def run():
    """Main social agent — runs every Monday morning."""
    now = datetime.now(PERTH_TZ)

    # Only run on Mondays
    if now.weekday() != 0:
        return

    logger.info("📱 Social Agent: Checking GHL Media Storage for new photos...")

    photos = get_unposted_photos()

    if not photos:
        logger.info("📸 No new photos to post this week.")
        logger.info("   → Francisco can upload photos via GHL → Media Storage")
        return

    # Use the most recently uploaded photo
    photo = sorted(photos, key=lambda x: x.get("updatedAt", ""), reverse=True)[0]
    filename = photo.get("name", "sea-breeze-property.jpg")
    file_id = photo.get("id", "")
    image_url = photo.get("url", "")

    logger.info(f"📸 Using photo: {filename}")

    # Generate caption
    caption = generate_caption(filename, image_url)
    hashtags = get_hashtags(filename)
    full_post = f"{caption}\n\n{hashtags}"

    # Schedule for Wednesday 9am
    days_until_wed = (2 - now.weekday()) % 7 or 7
    post_time = (now + timedelta(days=days_until_wed)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    post_time_display = post_time.strftime("%A %d %B at 9:00am")
    post_time_iso = post_time.isoformat()

    logger.info(f"📅 Scheduling for: {post_time_display}")
    logger.info(f"📝 Caption:\n{full_post[:200]}...")

    # Try Social Planner first, fallback to note
    scheduled = schedule_post(full_post, image_url, post_time_iso)

    if scheduled:
        logger.info(f"✅ Post scheduled via GHL Social Planner!")
        mark_as_posted(file_id, filename)
    else:
        save_caption_as_note(full_post, filename, post_time_display)
        mark_as_posted(file_id, filename)

    logger.info("📱 Social Agent: Done.")
