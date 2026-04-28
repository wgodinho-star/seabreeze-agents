"""
Anthropic Claude API wrapper.
All agent reasoning goes through this module.
"""
import os
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"

SEABREEZE_CONTEXT = """
You are an AI agent working for Sea Breeze Maintenance Pty Ltd in Perth, WA.
Owner: Francisco Da Silva
Services: grounds maintenance, gutter cleaning, garden maintenance, 
          lawn mowing, green waste removal, strata maintenance, 
          aged care facility maintenance.
Tone: friendly, professional, local Perth business.
Always be concise — these are SMS/email replies, not essays.
"""


def think(system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
    """Send a prompt to Claude and get a response."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=SEABREEZE_CONTEXT + "\n\n" + system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


def qualify_lead(name: str, service_requested: str, suburb: str) -> dict:
    """Use Claude to qualify a lead and decide next action."""
    result = think(
        system_prompt="""Qualify this inbound lead. 
        Return JSON with keys: 
        - score (hot/warm/cold)
        - priority (high/medium/low) 
        - suggested_action (call_now/send_quote/nurture)
        - response_sms (a friendly SMS reply under 160 chars)
        Return ONLY valid JSON, no other text.""",
        user_message=f"Name: {name}, Service: {service_requested}, Suburb: {suburb}"
    )
    import json
    try:
        return json.loads(result)
    except Exception:
        return {
            "score": "warm",
            "priority": "medium",
            "suggested_action": "send_quote",
            "response_sms": f"Hi {name}! Thanks for reaching out to Sea Breeze Maintenance. We'll be in touch shortly to discuss your {service_requested} needs! 🌿"
        }


def generate_sms_reply(contact_name: str, service: str, context: str = "") -> str:
    """Generate a personalised SMS reply for a new lead."""
    return think(
        system_prompt="Write a friendly, professional SMS reply (max 160 chars). No emojis overload. Perth local business feel.",
        user_message=f"New lead: {contact_name} wants {service}. Context: {context}"
    )


def generate_quote_email(contact_name: str, service: str,
                          suburb: str, details: str = "") -> str:
    """Generate a quote follow-up email."""
    return think(
        system_prompt="Write a professional quote follow-up email for a grounds maintenance business. Keep it warm and local.",
        user_message=f"Client: {contact_name}, Service: {service}, Suburb: {suburb}, Details: {details}",
        max_tokens=400
    )


def generate_review_request(contact_name: str, service_completed: str) -> str:
    """Generate a Google review request SMS."""
    return think(
        system_prompt="Write a friendly SMS asking for a Google review. Max 160 chars. Include a placeholder [GOOGLE_LINK].",
        user_message=f"Client {contact_name} just had {service_completed} completed by Sea Breeze Maintenance."
    )


def generate_weekly_report(leads: list, jobs: list, revenue: float) -> str:
    """Generate Francisco's weekly summary report."""
    return think(
        system_prompt="Write a concise weekly business summary for the business owner. Use bullet points. Keep it under 200 words.",
        user_message=f"New leads this week: {len(leads)}, Jobs completed: {len(jobs)}, Estimated revenue: ${revenue}. Lead details: {leads}",
        max_tokens=600
    )
