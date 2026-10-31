from datetime import datetime, timedelta

from _gen import *  # <AUTO GENERATED>
from functions import api_client, idnv
from functions.in_hours import in_hours
from functions.utils import site_timezone, variant_attr


def set_time(conv: Conversation):
    timezone_str, timezone = site_timezone(conv)

    now = datetime.now(timezone)
    conv.state.timezone = timezone_str
    conv.state.datetime_now = now
    conv.state.today_iso = now.date().isoformat()
    conv.state.formatted_date_time = now.strftime("%A, %B %d, %Y at %I:%M %p")
    conv.state.date_guide = date_guide(now.date())


def date_guide(today) -> str:
    """Dates the model needs to turn "Friday", "later this week" or "next week" into
    YYYY-MM-DD without doing calendar arithmetic itself."""
    days = [today + timedelta(days=n) for n in range(1, 15)]
    this_week = [d for d in days if d.isocalendar()[1] == today.isocalendar()[1]]
    next_monday = next(d for d in days if d.weekday() == 0)
    listing = ", ".join(
        f"{d.strftime('%A %B')} {d.day} = {d.isoformat()}" for d in days[:8]
    )
    rest = ", ".join(d.isoformat() for d in this_week) or "none (today is the last day)"
    return (
        f"Next 8 days: {listing}. Rest of this week: {rest}. "
        f"Next week starts Monday {next_monday.isoformat()}."
    )


def _caller_phone(conv: Conversation) -> str:
    """The caller ID as ten digits, or "" when there is none. No caller ID (a Studio chat or
    simulation without a caller number, an in-app call's email address) is never treated as a
    fixture account, in mock mode or not: verification asks."""
    digits = idnv.normalize_phone(conv.caller_number or "")
    return digits if idnv.is_valid_phone(digits) else ""


def start_function(conv: Conversation):
    set_time(conv)
    conv.state.incontact_id = conv.sip_headers.get("X-InContact-ContactId")
    conv.state.caller_phone = _caller_phone(conv)
    # The SMS templates can only read state variables, not variant attributes.
    conv.state.site_name = variant_attr(conv, "site_name")
    conv.state.customer_portal_url = variant_attr(conv, "customer_portal_url")

    # Lax ID&V from the caller ID: one account on this number verifies the caller.
    idnv.state(conv)
    if conv.state.caller_phone:
        idnv.match_ani(
            conv,
            conv.state.caller_phone,
            lambda phone: api_client.find_customers_by_phone(conv, phone),
        )

    settings = (conv.real_time_config or {}).get("settings", {})
    conv.state.is_ooh = bool(settings.get("hours_sensitive", False)) and not in_hours(
        conv
    )
    if conv.state.is_ooh:
        conv.write_metric("OOH")
        conv.state.hours_mode_instructions = (
            "## Out of hours\n"
            "The office is closed. You can still book, check, move and cancel visits and answer "
            "questions. For anything that needs a person, say: \"I'm only able to help with "
            "visits and general questions right now. Please call back during business hours "
            "for help with that.\" Don't transfer."
        )
    else:
        conv.state.hours_mode_instructions = ""
    return {"utterance": ""}
