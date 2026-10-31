from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from functions.in_hours import in_hours
from functions.utils import variant_timezone

from _gen import *  # <AUTO GENERATED>
from functions import api_client, idnv


def set_time(conv: Conversation):
    timezone_str = variant_timezone(conv)
    timezone = ZoneInfo(timezone_str)
    now = datetime.now(timezone)
    conv.state.timezone = timezone_str
    conv.state.datetime_now = now
    conv.state.today_iso = now.date().isoformat()
    conv.state.formatted_date_time = now.strftime("%A, %B %d, %Y at %I:%M %p")
    conv.state.date_guide = date_guide(now.date())


def date_guide(today) -> str:
    """Dates the model needs to talk about "Friday" or "next week" without doing
    calendar arithmetic itself."""
    days = [today + timedelta(days=n) for n in range(1, 8)]
    listing = ", ".join(
        f"{d.strftime('%A %B')} {d.day} = {d.isoformat()}" for d in days
    )
    return f"Next 7 days: {listing}."


def _caller_phone(conv: Conversation) -> str:
    """The caller ID as ten digits, or '' when there is none. A chat or simulation with no
    caller number (or an email address, as in-app calls send) has no caller ID, in mock
    mode too: verification asks for the number."""
    digits = idnv.normalize_phone(conv.caller_number or "")
    return digits if idnv.is_valid_phone(digits) else ""


def start_function(conv: Conversation):
    set_time(conv)
    conv.state.caller_phone = _caller_phone(conv)
    # SMS templates read state variables, not variant attributes.
    conv.state.site_name = conv.variant.site_name if conv.variant else ""

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
            "The store is closed. You can still track, cancel and re-address orders and "
            "answer questions. For anything that needs a person, say: \"I'm only able to help "
            "with orders and general questions right now. Please call back when we're open.\" Don't transfer."
        )
    else:
        conv.state.hours_mode_instructions = ""
    return {"utterance": ""}
