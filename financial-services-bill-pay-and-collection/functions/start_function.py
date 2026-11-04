from _gen import *  # <AUTO GENERATED>
from functions import billing, hours, idnv
from functions.handoff_utils import is_vulnerable_customer


def _attr(conv, name: str) -> str:
    return (getattr(conv.variant, name, "") or "").strip() if conv.variant else ""


def _caller_phone(conv: Conversation) -> str:
    digits = idnv.normalize_phone(conv.caller_number or "")
    return digits if idnv.is_valid_phone(digits) else ""


def _upfront_message(conv) -> str:
    upfront = (conv.real_time_config or {}).get("upfront_messaging", {}) or {}
    message = ""
    if upfront.get("disclaimer_active"):
        message += upfront.get("disclaimer", "")
    if upfront.get("emergency_active"):
        message += " " + upfront.get("emergency_message", "")
    message = message.strip()
    if message and not message.endswith("."):
        message += "."
    return message


def greeting(company: str) -> str:
    return (
        f"Hi, thanks for calling {company or 'us'}. You're speaking with our virtual assistant. "
        "How can I help?"
    )


def start_function(conv: Conversation):
    now = hours.now(conv)
    conv.state.today_iso = now.date().isoformat()
    conv.state.formatted_date_time = now.strftime("%A, %B %d, %Y at %I:%M %p")
    conv.state.date_guide = hours.date_guide(now.date())
    conv.state.caller_phone = _caller_phone(conv)
    # SMS templates and topics can only read state variables, not variant attributes.
    company = _attr(conv, "site_name")
    conv.state.site_name = company
    conv.state.website_url = _attr(conv, "website_url")
    # Numbers we say first, digit by digit (design section 3).
    conv.state.phone_number_spoken = billing.say_phone(_attr(conv, "phone_number"))
    conv.state.fraud_line_spoken = billing.say_phone(_attr(conv, "fraud_phone_number"))
    # The contact_centre_hours topic reads this, so it never renders a blank attribute.
    conv.state.opening_hours_line = hours.hours_line(conv)
    idnv.state(conv)  # strict ID&V: the caller ID alone never verifies

    conv.state.is_vulnerable_customer = is_vulnerable_customer(conv)
    if conv.state.is_vulnerable_customer:
        conv.write_metric("VULNERABLE_CUSTOMER", write_once=True)
    conv.functions.vc_keywords()

    if conv.channel_type == "webchat.polyai":
        return {
            "utterance": f"Thanks for contacting {company or 'us'}. How can I help?"
        }

    # Out of hours, the call goes on as normal: only transfers change (functions/handoff.py).
    if hours.is_out_of_hours(conv, now):
        conv.write_metric("OOH_CALL", write_once=True)
    upfront = _upfront_message(conv)
    return {"utterance": f"{upfront} {greeting(company)}".strip()}
