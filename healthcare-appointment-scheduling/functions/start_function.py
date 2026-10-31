from _gen import *  # <AUTO GENERATED>
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import functions.appointments as appointments
import functions.idnv as idnv

DEFAULT_TIMEZONE = "America/New_York"


def local_now(conv: Conversation) -> tuple[str, datetime]:
    """The variant's timezone (DEFAULT_TIMEZONE if unset or invalid) and the time there."""
    variant = conv.variant
    timezone_str = (
        getattr(variant, "timezone", "") if variant else ""
    ) or DEFAULT_TIMEZONE
    try:
        timezone = ZoneInfo(timezone_str)
    except Exception as e:
        conv.log.warning(
            "Invalid timezone in config", timezone=timezone_str, error=str(e)
        )
        timezone_str, timezone = DEFAULT_TIMEZONE, ZoneInfo(DEFAULT_TIMEZONE)
    return timezone_str, datetime.now(timezone)


def set_time(conv: Conversation):
    timezone_str, now = local_now(conv)
    conv.state.timezone = timezone_str
    conv.state.datetime_now = now
    conv.state.today_iso = now.date().isoformat()
    conv.state.formatted_date_time = now.strftime("%A, %B %d, %Y at %I:%M %p")
    conv.state.date_guide = date_guide(now.date())
    return now


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


def _is_ooh(conv: Conversation, now: datetime) -> bool:
    """Outside the opening_hours attribute. In draft, sandbox and pre-release,
    real-time config `ooh_slider` (or flags.ooh_forced) forces it on or off."""
    config = conv.real_time_config or {}
    flags = config.get("flags") or {}
    forced = config.get("ooh_slider")
    if forced is None and isinstance(flags, dict):
        forced = flags.get("ooh_forced")
    if conv.env in ("draft", "sandbox", "pre-release") and forced is not None:
        return bool(forced)
    return not appointments.is_open_at(conv, now)


def start_function(conv: Conversation):
    now = set_time(conv)
    conv.write_metric("CALLEE_NUMBER", conv.callee_number)

    caller = idnv.normalize_phone(conv.caller_number or "")
    conv.state.caller_phone = caller if idnv.is_valid_phone(caller) else ""
    # Company copy for SMS templates, which can only read state variables.
    variant = conv.variant
    conv.state.site_name = (getattr(variant, "site_name", "") or "") if variant else ""
    conv.state.address = (getattr(variant, "address", "") or "") if variant else ""
    conv.state.opening_hours_spoken = appointments.say_opening_hours(conv)

    # Strict ID&V: the caller ID never verifies anyone on its own.
    idnv.state(conv)

    after_hours = (getattr(variant, "after_hours_info", "") or "") if variant else ""
    conv.state.is_ooh = _is_ooh(conv, now)
    if conv.state.is_ooh:
        conv.write_metric("OOH", write_once=True)
        if appointments.hours_known(conv):
            hours_line = f"give the opening hours ({conv.state.opening_hours_spoken})"
        else:
            # Blank hours: the default decides when we're closed but is never spoken.
            hours_line = f'say "{conv.state.opening_hours_spoken}"'
        conv.state.hours_mode_instructions = (
            "## Out of hours\n"
            "The clinic is closed right now. You can still book, check, move and cancel "
            "appointments and answer questions. For anything that needs a person (except an "
            f"emergency), say we're closed, {hours_line} and tell them what to do while we're "
            f"closed: {after_hours} Don't transfer."
        )
    else:
        conv.state.hours_mode_instructions = ""
    return {"utterance": ""}
