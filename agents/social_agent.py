"""
Social Media Agent — auto-generates and schedules weekly content for Sea Breeze.
One post per week. Wander provides the photo, agent writes the caption.
Runs every Monday, generates content for the week.

Platforms: Facebook + Instagram via GHL Social Planner
Topics rotate: Safety tip / Before-after / Service spotlight / Client story / Seasonal
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

TOPICS = [
    "safety_tip",
    "service_spotlight_gutters",
    "service_spotlight_garden",
    "service_spotlight_pressure",
    "service_spotlight_antislip",
    "seasonal_tip",
    "client_story",
    "aged_care_focus",
    "strata_focus",
    "team_intro",
]

HASHTAGS = {
    "base": "#SeaBreezeMaintenance #PerthMaintenance #PropertySafety #WesternAustralia",
    "aged_care": "#AgedCare #AgedCareSafety #PropertyMaintenance #Perth",
    "strata": "#StrataManagement #BodyCorporate #PropertyManagement #Perth",
    "gutter": "#GutterCleaning #PreventiveMaintenance #HomeMaintenancePerth",
    "garden": "#GardenMaintenance #LandscapingPerth #GroundsMaintenanceWA",
    "pressure": "#PressureWashing #PropertyClean #DrivewayClean #PerthCleaning",
    "antislip": "#AntiSlip #FallsPrevention #SafetyFirst #PropertySafety",
    "southwest": "#Dunsborough #Busselton #MargaretRiver #SouthWestWA",
}


def get_week_topic(week_num: int) -> str:
    """Rotate through topics week by week."""
    return TOPICS[week_num % len(TOPICS)]


def generate_caption(topic: str, image_description: str = "") -> str:
    """Generate a social media caption using Claude."""

    topic_prompts = {
        "safety_tip": """Write a Facebook/Instagram post for Sea Breeze Maintenance sharing a practical property safety tip.
Topic: preventing water damage from blocked gutters in Perth's winter rain season.
Include: the safety risk, our service (preventive gutter works), call to action.
Tone: warm, local, helpful — like a trusted local business, not corporate.""",

        "service_spotlight_gutters": """Write a Facebook/Instagram post spotlighting Sea Breeze Maintenance's Preventive Gutter Works service.
Angle: prevention is cheaper than repair. Perth winters + blocked gutters = water damage.
Include a call to action: free inspection offer.
Tone: professional but friendly, local Perth/SW WA feel.""",

        "service_spotlight_garden": """Write a Facebook/Instagram post about Sea Breeze Maintenance's garden and grounds maintenance.
Focus: well-kept gardens reduce fire risk and trip hazards — especially important for aged care and strata.
Mention: Perth metro + Dunsborough/SW WA service area.
Tone: warm, community-focused.""",

        "service_spotlight_pressure": """Write a Facebook/Instagram post about Sea Breeze's pressure washing service.
Focus: dirty driveways and paths are a safety hazard — slip risk for elderly residents.
Great for: aged care facilities, strata common areas, residential driveways.
Include: free quote offer. Tone: safety-focused but friendly.""",

        "service_spotlight_antislip": """Write a Facebook/Instagram post about anti-slip surface installation.
Focus: falls are the #1 cause of injury in aged care. Our anti-slip surfaces protect residents.
Target: aged care facility managers and strata property managers.
Tone: professional, safety-focused, warm.""",

        "seasonal_tip": """Write a seasonal property safety tip post for Sea Breeze Maintenance.
Current season context: Western Australia, approaching winter.
Tip: pre-winter property checklist — gutters, pathways, garden overgrowth.
Position Sea Breeze as the solution. Tone: helpful, local.""",

        "client_story": """Write a social proof post for Sea Breeze Maintenance.
Format: brief client success story (no real names — use "a local aged care facility" or "a Dunsborough homeowner").
Story: they called because of a blocked gutter causing water damage. Sea Breeze fixed it fast and did a full preventive inspection.
Tone: warm, trustworthy, local.""",

        "aged_care_focus": """Write a post specifically targeting aged care facility managers in Perth.
Message: Sea Breeze Maintenance specialises in safety maintenance for aged care properties.
Services: garden maintenance, preventive gutter works, anti-slip surfaces, pressure washing.
Angle: compliance, resident safety, liability reduction.
Tone: professional, caring.""",

        "strata_focus": """Write a post targeting strata and body corporate property managers in Perth.
Message: Sea Breeze Maintenance maintains strata properties across Perth and SW WA.
Services: common area maintenance, gutter cleaning, pressure washing, grounds.
Angle: liability reduction, body corporate compliance, professional service.
Tone: B2B professional but approachable.""",

        "team_intro": """Write a friendly 'about us' style post for Sea Breeze Maintenance.
Brand as a team — not a one-man show.
Service area: Perth metro and SW WA (Dunsborough, Busselton, Margaret River).
Focus: reliable, professional, safety-first team.
Tone: warm, community-focused, genuine.""",
    }

    prompt = topic_prompts.get(topic, topic_prompts["safety_tip"])
    if image_description:
        prompt += f"\n\nThe accompanying photo shows: {image_description}"

    prompt += "\n\nKeep the post under 200 words. Use 2-3 line breaks for readability. End with relevant hashtags."

    return claude_ai.think(
        system_prompt="""You write engaging social media content for Sea Breeze Maintenance, 
a property safety and maintenance team in Perth and South West WA. 
Brand voice: professional, warm, safety-focused, local community.
Services: garden maintenance, preventive gutter works, pressure washing, anti-slip surfaces.
Target: aged care facilities, strata managers, homeowners.""",
        user_message=prompt,
        max_tokens=350
    )


def schedule_post(caption: str, scheduled_time: str,
                  platforms: list = None) -> dict:
    """Schedule a post via GHL Social Planner API."""
    if platforms is None:
        platforms = ["facebook", "instagram"]

    try:
        r = requests.post(
            f"https://services.leadconnectorhq.com/social-media-posting/{LOC}/post",
            headers=HEADERS,
            json={
                "locationId": LOC,
                "type": "post",
                "summary": caption,
                "scheduleDate": scheduled_time,
                "platforms": platforms,
                "status": "scheduled"
            }
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def generate_weekly_content(image_description: str = "") -> dict:
    """Generate this week's social post content."""
    now = datetime.now(PERTH_TZ)
    week_num = now.isocalendar()[1]
    topic = get_week_topic(week_num)

    # Generate caption
    caption = generate_caption(topic, image_description)

    # Schedule for Wednesday 9am next week
    days_until_wed = (2 - now.weekday()) % 7
    if days_until_wed == 0:
        days_until_wed = 7
    post_time = (now + timedelta(days=days_until_wed)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )

    return {
        "topic": topic,
        "caption": caption,
        "scheduled_for": post_time.strftime("%A %d %B at 9:00am"),
        "scheduled_iso": post_time.isoformat(),
        "week": week_num,
        "hashtags": f"{HASHTAGS['base']} {HASHTAGS.get(topic.split('_')[0], '')}"
    }


def run():
    """Run social agent — generate and log weekly content."""
    now = datetime.now(PERTH_TZ)

    # Only run on Mondays
    if now.weekday() != 0:
        return

    logger.info("📱 Social Agent: Generating weekly content...")

    content = generate_weekly_content()

    logger.info(f"📱 Topic: {content['topic']}")
    logger.info(f"📱 Scheduled for: {content['scheduled_for']}")
    logger.info(f"📱 Caption preview:\n{content['caption'][:200]}...")

    # Try to schedule via GHL
    result = schedule_post(
        content["caption"],
        content["scheduled_iso"]
    )

    if result.get("error") or result.get("statusCode") == 404:
        # GHL Social API not available — save as note on Francisco's contact
        note = (
            f"SOCIAL MEDIA POST — Week {content['week']}\n"
            f"Topic: {content['topic']}\n"
            f"Schedule: {content['scheduled_for']}\n"
            f"{'='*40}\n"
            f"{content['caption']}\n"
            f"{'='*40}\n"
            f"ACTION: Copy caption above and post to Facebook/Instagram\n"
            f"or connect Social Planner in GHL to auto-post."
        )
        requests.post(
            f"https://services.leadconnectorhq.com/contacts/{os.getenv('GHL_FRANCISCO_CONTACT_ID')}/notes",
            headers=HEADERS,
            json={"body": note}
        )
        logger.info(f"📱 Caption saved to GHL notes (Social Planner not connected)")
    else:
        logger.info(f"📱 Post scheduled successfully!")

    logger.info("📱 Social Agent: Done.")
