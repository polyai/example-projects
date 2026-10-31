from _gen import *  # <AUTO GENERATED>
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import functions.api_client as api_client
import functions.hours as hours
import functions.idnv as idnv

DEFAULT_TIMEZONE = "America/New_York"


def set_time(conv: Conversation):
    """The restaurant's local time, from the `timezone` variant attribute (per site)."""
    timezone_str = (
        getattr(conv.variant, "timezone", "") if conv.variant else ""
    ) or DEFAULT_TIMEZONE
    try:
        timezone = ZoneInfo(timezone_str)
    except Exception as e:
        conv.log.warning(
            "Invalid timezone attribute", timezone=timezone_str, error=str(e)
        )
        timezone_str, timezone = DEFAULT_TIMEZONE, ZoneInfo(DEFAULT_TIMEZONE)

    now = datetime.now(timezone)
    conv.state.timezone = timezone_str
    conv.state.now_iso = now.replace(tzinfo=None).isoformat(timespec="minutes")
    conv.state.today_iso = now.date().isoformat()
    conv.state.formatted_date_time = now.strftime("%A, %B %d, %Y at %I:%M %p")
    conv.state.date_guide = date_guide(now.date())


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = (
        date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    ) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def holidays(today: date) -> list[tuple[date, str]]:
    """US holidays restaurants get asked about, for the next twelve months."""
    found = []
    for y in (today.year, today.year + 1):
        found += [
            (date(y, 1, 1), "New Year's Day"),
            (date(y, 2, 14), "Valentine's Day"),
            (_nth_weekday(y, 5, 6, 2), "Mother's Day"),
            (_last_weekday(y, 5, 0), "Memorial Day"),
            (_nth_weekday(y, 6, 6, 3), "Father's Day"),
            (date(y, 7, 4), "Independence Day"),
            (_nth_weekday(y, 9, 0, 1), "Labor Day"),
            (_nth_weekday(y, 11, 3, 4), "Thanksgiving"),
            (date(y, 12, 24), "Christmas Eve"),
            (date(y, 12, 25), "Christmas Day"),
            (date(y, 12, 31), "New Year's Eve"),
        ]
    return sorted((d, n) for d, n in found if today <= d < today + timedelta(days=366))


def date_guide(today: date) -> str:
    """Dates the model needs to turn "Friday", "this weekend" or "Christmas Eve" into
    YYYY-MM-DD without doing calendar arithmetic itself."""
    days = [today + timedelta(days=n) for n in range(1, 15)]
    listing = ", ".join(
        f"{d.strftime('%A %B')} {d.day} = {d.isoformat()}" for d in days[:8]
    )
    next_monday = next(d for d in days if d.weekday() == 0)
    named = ", ".join(f"{name} = {d.isoformat()}" for d, name in holidays(today))
    return (
        f"Today = {today.isoformat()}. Next 8 days: {listing}. "
        f"Next week starts Monday {next_monday.isoformat()}. Holidays: {named}."
    )


def _caller_phone(conv: Conversation) -> str:
    """The caller ID as ten digits, or empty. No caller ID (a Studio chat or simulation, an
    in-app call's email address) means no caller ID, in mock mode too: verification asks."""
    digits = idnv.normalize_phone(conv.caller_number or "")
    return digits if idnv.is_valid_phone(digits) else ""


def start_function(conv: Conversation):
    set_time(conv)
    conv.state.caller_phone = _caller_phone(conv)
    # SMS templates can only read state variables, not variant attributes.
    conv.state.site_name = (conv.variant.site_name if conv.variant else "") or ""

    # Lax ID&V from the caller ID: one guest on this number verifies the caller
    # for finding their bookings. A new booking needs no verification.
    idnv.state(conv)
    if conv.state.caller_phone:
        idnv.match_ani(
            conv,
            conv.state.caller_phone,
            lambda phone: api_client.find_guests_by_phone(conv, phone),
        )

    open_now = hours.is_open_at(conv, datetime.fromisoformat(conv.state.now_iso))
    conv.state.is_ooh = not open_now
    if not open_now:
        conv.write_metric("OOH", write_once=True)
