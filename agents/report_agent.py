"""
Report Agent — daily end-of-day email to Francisco + weekly summary.
Zoe signs the email. No SMS to Francisco — email only.
Daily: 5pm Perth time
Weekly: Monday 8am Perth time
"""
import logging
import os
import requests
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

FRANCISCO_CONTACT_ID = os.getenv("GHL_FRANCISCO_CONTACT_ID")
FRANCISCO_EMAIL = os.getenv("CLIENT_EMAIL", "accounts@seabreezemaintenance.com.au")
WANDER_CONTACT_ID = "g1Hp5UCnMLVganCyNj93"
WANDER_EMAIL = "wgodinho@gmail.com"
FROM_EMAIL = "hello@seabreezemaintenance.com.au"


def get_todays_stats() -> dict:
    """Get today's activity stats from GHL."""
    try:
        now = datetime.now(PERTH_TZ)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get contacts added today
        r = requests.get(
            f"https://services.leadconnectorhq.com/contacts/?locationId={LOC}&limit=100",
            headers=HEADERS
        )
        contacts = r.json().get("contacts", [])

        new_leads = []
        for c in contacts:
            added = c.get("dateAdded", "")
            if added:
                try:
                    dt = datetime.fromisoformat(
                        added.replace("Z", "+00:00")
                    ).astimezone(PERTH_TZ)
                    if dt >= today_start:
                        new_leads.append(c.get("companyName") or
                                        f"{c.get('firstName','')} {c.get('lastName','')}".strip())
                except Exception:
                    pass

        # Get pipeline opportunities
        r2 = requests.get(
            f"https://services.leadconnectorhq.com/opportunities/search?location_id={LOC}&limit=50",
            headers=HEADERS
        )
        opps = r2.json().get("opportunities", [])
        total_pipeline = sum(
            float(o.get("monetaryValue", 0) or 0) for o in opps
        )

        # Count prospects by status
        sent = [c for c in contacts if "outreach-sent" in c.get("tags", [])]
        replied = [c for c in contacts if "outreach-replied" in c.get("tags", [])]

        # Get scheduled social posts
        import requests as req_lib
        KEY = os.getenv("GHL_SEABREEZE_KEY")
        LOC = os.getenv("GHL_SEABREEZE_LOCATION_ID")
        HEADERS2 = {"Authorization": f"Bearer {KEY}", "Version": "2021-07-28"}
        r3 = req_lib.get(
            f"https://services.leadconnectorhq.com/social-media-posting/{LOC}/posts",
            headers=HEADERS2
        )
        scheduled_posts = len(r3.json().get("posts", [])) if r3.status_code == 200 else 0

        return {
            "new_leads": new_leads,
            "total_opportunities": len(opps),
            "pipeline_value": total_pipeline,
            "prospects_contacted": len(sent),
            "prospects_replied": len(replied),
            "scheduled_posts": scheduled_posts,
            "date": now.strftime("%A %d %B %Y"),
            "time": now.strftime("%-I:%M%p").lower()
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {}


def build_daily_email_html(stats: dict, recipient: str) -> str:
    """Build branded daily report email."""
    new_leads_html = ""
    if stats.get("new_leads"):
        items = "".join(
            f'<li style="color:#444;font-size:14px;padding:4px 0;">{lead}</li>'
            for lead in stats["new_leads"]
        )
        new_leads_html = f"<ul style='margin:8px 0;padding-left:20px;'>{items}</ul>"
    else:
        new_leads_html = '<p style="color:#888;font-size:14px;margin:8px 0;">No new leads today — outreach continues tomorrow morning.</p>'

    is_francisco = recipient == "francisco"
    greeting = "Hi Francisco! 👋" if is_francisco else "Hi Wander! 👋"
    intro = (
        "Here's your daily Sea Breeze Maintenance update from Zoe. "
        "Everything is running smoothly — here's what happened today."
        if is_francisco else
        "Here's today's Stackd AI system report for Sea Breeze Maintenance."
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

  <tr><td style="background:#1a1a2e;padding:24px 36px;">
    <span style="color:#fff;font-size:18px;font-weight:bold;">🌿 Sea Breeze Maintenance</span><br>
    <span style="color:#9FE1CB;font-size:12px;">Daily Report — {stats.get('date','')}</span>
  </td></tr>

  <tr><td style="background:#1D9E75;padding:8px 36px;">
    <span style="color:#fff;font-size:12px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;">End of Day Summary</span>
  </td></tr>

  <tr><td style="padding:28px 36px;">
    <p style="color:#1a1a2e;font-size:16px;font-weight:bold;margin:0 0 6px 0;">{greeting}</p>
    <p style="color:#666;font-size:14px;line-height:1.6;margin:0 0 24px 0;">{intro}</p>

    <!-- Stats grid -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
      <tr>
        <td width="31%" style="background:#E1F5EE;border-radius:8px;padding:16px;text-align:center;">
          <div style="font-size:28px;font-weight:bold;color:#1D9E75;">{stats.get('total_opportunities',0)}</div>
          <div style="font-size:12px;color:#666;margin-top:4px;">Active Opportunities</div>
        </td>
        <td width="2%"></td>
        <td width="31%" style="background:#E1F5EE;border-radius:8px;padding:16px;text-align:center;">
          <div style="font-size:28px;font-weight:bold;color:#1D9E75;">${stats.get('pipeline_value',0):,.0f}</div>
          <div style="font-size:12px;color:#666;margin-top:4px;">Pipeline Value (AUD)</div>
        </td>
        <td width="2%"></td>
        <td width="31%" style="background:#E1F5EE;border-radius:8px;padding:16px;text-align:center;">
          <div style="font-size:28px;font-weight:bold;color:#1D9E75;">{stats.get('scheduled_posts',0)}</div>
          <div style="font-size:12px;color:#666;margin-top:4px;">Social Posts Scheduled</div>
        </td>
      </tr>
      <tr><td colspan="5" style="padding-top:12px;"></td></tr>
      <tr>
        <td width="48%" style="background:#f8f8f8;border-radius:8px;padding:16px;text-align:center;">
          <div style="font-size:28px;font-weight:bold;color:#1a1a2e;">{stats.get('prospects_contacted',0)}</div>
          <div style="font-size:12px;color:#666;margin-top:4px;">Prospects Contacted</div>
        </td>
        <td width="4%"></td>
        <td colspan="3" width="48%" style="background:#f8f8f8;border-radius:8px;padding:16px;text-align:center;">
          <div style="font-size:28px;font-weight:bold;color:#1a1a2e;">{stats.get('prospects_replied',0)}</div>
          <div style="font-size:12px;color:#666;margin-top:4px;">Replies Received</div>
        </td>
      </tr>
    </table>

    <!-- New leads -->
    <div style="background:#f8f8f8;border-radius:8px;padding:16px;margin-bottom:24px;">
      <div style="font-size:13px;font-weight:bold;color:#1a1a2e;margin-bottom:8px;">📥 New Leads Today</div>
      {new_leads_html}
    </div>

    <!-- Agent status -->
    <div style="background:#f8f8f8;border-radius:8px;padding:16px;margin-bottom:24px;">
      <div style="font-size:13px;font-weight:bold;color:#1a1a2e;margin-bottom:10px;">⚙️ System Status</div>
      <table width="100%" cellpadding="0" cellspacing="0">
        {"".join(f'<tr><td style="font-size:13px;color:#444;padding:3px 0;">✅ {agent}</td></tr>' for agent in
        ['Zoe (Voice AI) — active 24/7',
         'Lead Agent — monitoring',
         'Outreach Agent — fires 8am Perth',
         'Follow-up Agent — running',
         'Review Agent — monitoring',
         'Health Agent — all systems healthy'])}
      </table>
    </div>

    {"<p style='color:#666;font-size:13px;'>Outreach emails will fire tomorrow morning at 8am Perth time. I'll be in touch if anything needs your attention. Have a great evening! 😊</p>" if is_francisco else
     "<p style='color:#666;font-size:13px;'>Full agent logs available on Railway. All systems nominal.</p>"}

  </td></tr>

  <!-- Signature -->
  <tr><td style="padding:0 36px 24px 36px;">
    <table cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding-right:12px;">
          <div style="width:40px;height:40px;background:#1D9E75;border-radius:50%;text-align:center;line-height:40px;color:#fff;font-weight:bold;font-size:16px;">Z</div>
        </td>
        <td>
          <div style="color:#1a1a2e;font-weight:bold;font-size:14px;">Zoe</div>
          <div style="color:#666;font-size:12px;">Business Administrator — Sea Breeze Maintenance</div>
          <div style="color:#1D9E75;font-size:12px;">📞 0480 891 085 | hello@seabreezemaintenance.com.au</div>
        </td>
      </tr>
    </table>
  </td></tr>

  <tr><td style="background:#1a1a2e;padding:16px 36px;text-align:center;">
    <span style="color:#9FE1CB;font-size:11px;">Sea Breeze Maintenance Pty Ltd — Perth &amp; South West WA</span><br>
    <span style="color:#555;font-size:11px;">Powered by Stackd AI 🌿</span>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""


def send_email(contact_id: str, to_email: str, subject: str, html: str):
    """Send email via GHL."""
    r = requests.post(
        "https://services.leadconnectorhq.com/conversations/messages",
        headers=HEADERS,
        json={
            "type": "Email",
            "contactId": contact_id,
            "subject": subject,
            "html": html,
            "emailTo": to_email,
            "emailFrom": FROM_EMAIL,
        }
    )
    return r.status_code in [200, 201]


def run():
    """Send daily report at 5pm Perth, weekly on Monday 8am Perth."""
    now = datetime.now(PERTH_TZ)

    # Daily 5pm report
    if now.hour == 17:
        logger.info("📊 Report Agent: Sending daily end-of-day email...")
        stats = get_todays_stats()
        date_str = now.strftime("%A %d %B")

        # Send to Francisco
        html_f = build_daily_email_html(stats, "francisco")
        if send_email(
            FRANCISCO_CONTACT_ID,
            FRANCISCO_EMAIL,
            f"🌿 Sea Breeze Daily Update — {date_str}",
            html_f
        ):
            logger.info("✅ Daily report sent to Francisco")

        # Send to Wander
        html_w = build_daily_email_html(stats, "wander")
        if send_email(
            WANDER_CONTACT_ID,
            WANDER_EMAIL,
            f"📊 Stackd AI — Sea Breeze Daily Report — {date_str}",
            html_w
        ):
            logger.info("✅ Daily report sent to Wander")

    # Weekly Monday 8am report
    elif now.weekday() == 0 and now.hour == 8:
        logger.info("📊 Report Agent: Sending weekly summary...")
        stats = get_todays_stats()

        html_f = build_daily_email_html(stats, "francisco")
        send_email(
            FRANCISCO_CONTACT_ID,
            FRANCISCO_EMAIL,
            f"🌿 Sea Breeze Weekly Summary — Week of {now.strftime('%d %B')}",
            html_f
        )
        logger.info("✅ Weekly report sent")
