"""Site facts from the variant: opening hours, timezone and other attributes.

Opening hours and timezone are variant attributes so that the per-site values
onboarding writes reach the agent. Switches (hours_sensitive, force_ooh_enabled)
stay in real-time config.
"""

from _gen import *  # <AUTO GENERATED>
import re
from datetime import datetime, timedelta
from itertools import groupby
from zoneinfo import ZoneInfo


DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DEFAULT_TIMEZONE = "America/Chicago"
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Said instead of the hours when `opening_hours` is blank or unreadable. Never a default
# schedule or a made-up time.
HOURS_NOT_TO_HAND = "I'm sorry, I don't have our opening hours in front of me."

SPOKEN_TIMEZONES = {
    "America/New_York": "eastern time",
    "America/Detroit": "eastern time",
    "America/Indiana/Indianapolis": "eastern time",
    "America/Toronto": "eastern time",
    "US/Eastern": "eastern time",
    "America/Chicago": "central time",
    "US/Central": "central time",
    "America/Denver": "mountain time",
    "America/Boise": "mountain time",
    "America/Phoenix": "mountain time",
    "US/Mountain": "mountain time",
    "America/Los_Angeles": "pacific time",
    "America/Vancouver": "pacific time",
    "US/Pacific": "pacific time",
    "America/Anchorage": "Alaska time",
    "Pacific/Honolulu": "Hawaii time",
    "Europe/London": "UK time",
}


def variant_attr(conv, name: str, default: str = ""):
    """A variant attribute, or `default` when it is missing or blank."""
    value = getattr(conv.variant, name, None) if conv.variant else None
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    return value.strip() if isinstance(value, str) else value


def site_timezone(conv) -> tuple[str, ZoneInfo]:
    """The site's IANA timezone from the `timezone` variant attribute."""
    name = variant_attr(conv, "timezone", DEFAULT_TIMEZONE)
    try:
        return name, ZoneInfo(name)
    except Exception as e:
        conv.log.warning(
            "Invalid timezone variant attribute", timezone=name, error=str(e)
        )
        return DEFAULT_TIMEZONE, ZoneInfo(DEFAULT_TIMEZONE)


def parse_opening_hours(text) -> dict:
    """Parse the `opening_hours` attribute into {"monday": "07:00-19:00", ...}.

    One line per day, e.g. "Monday: 07:00-19:00" or "Sunday: closed". A line keyed
    by a date ("2026-12-25: closed") overrides that date. Days not listed are closed;
    lines that don't parse are skipped.
    """
    if isinstance(text, dict):
        items = list(text.items())
    else:
        items = [
            line.split(":", 1) for line in str(text or "").splitlines() if ":" in line
        ]
    hours = {}
    for key, value in items:
        key, value = str(key).strip().lower(), str(value).strip()
        if key in DAYS or _ISO_DATE.match(key):
            hours[key] = value or "closed"
    return hours


def site_opening_hours(conv) -> dict:
    return parse_opening_hours(variant_attr(conv, "opening_hours"))


def spoken_timezone(timezone_name: str) -> str:
    return SPOKEN_TIMEZONES.get(timezone_name, "local time")


def _fmt_time(t: str) -> str:
    h, m = map(int, t.strip().split(":"))
    if h in (0, 24) and m == 0:
        return "midnight"
    if h == 12 and m == 0:
        return "noon"
    period = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}{period}" if m else f"{h12}{period}"


def _fmt_hours(hours: str) -> str:
    start, end = hours.split("-")
    return f"{_fmt_time(start)} to {_fmt_time(end)}"


def _fmt_day_range(days: list[str]) -> str:
    if len(days) == 1:
        return days[0].capitalize()
    return f"{days[0].capitalize()} through {days[-1].capitalize()}"


def opening_hours_utterance(
    opening_hours: dict, timezone_name: str = DEFAULT_TIMEZONE
) -> str:
    """Turn parsed opening hours into a spoken sentence.

    Consecutive days with the same hours are grouped into ranges; closed days
    break a range, so Mon and Wed open with Tue closed never becomes "Monday
    through Wednesday".

    Example: {"monday": "07:00-19:00", "tuesday": "07:00-19:00", "saturday": "07:00-16:00"}
    with America/Chicago -> "We're open Monday through Tuesday 7am to 7pm, and
    Saturday 7am to 4pm, central time."

    Returns an empty string when no day has hours.
    """
    schedule = [(d, str(opening_hours.get(d, "closed"))) for d in DAYS]
    groups = []
    for hours, items in groupby(schedule, key=lambda x: x[1]):
        if hours.strip().lower() in ("closed", "close", ""):
            continue
        groups.append(([d for d, _ in items], hours))
    if not groups:
        return ""

    parts = [f"{_fmt_day_range(days)} {_fmt_hours(hours)}" for days, hours in groups]
    if len(parts) == 1:
        listing = parts[0]
    elif len(parts) == 2:
        listing = f"{parts[0]}, and {parts[1]}"
    else:
        listing = f"{', '.join(parts[:-1])}, and {parts[-1]}"
    return f"We're open {listing}, {spoken_timezone(timezone_name)}."


def site_hours_utterance(conv) -> str:
    """The site's opening hours as a sentence, or "" if not set or unreadable."""
    try:
        name, _ = site_timezone(conv)
        return opening_hours_utterance(site_opening_hours(conv), name)
    except Exception as e:
        conv.log.warning("Could not build opening hours utterance", error=str(e))
        return ""


def _clock(t: str) -> str:
    """'07:00' -> '7', '19:30' -> '7:30', '12:00' -> 'noon': how a time is said in a sentence."""
    h, m = map(int, t.strip().split(":"))
    if h in (0, 24) and m == 0:
        return "midnight"
    if h == 12 and m == 0:
        return "noon"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}" if m else f"{h12}"


def _span(hours: str):
    """'07:00-19:00' -> ('07:00', '19:00'), or None for a closed or unreadable day."""
    m = re.fullmatch(r"\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*", str(hours or ""))
    return (m.group(1).zfill(5), m.group(2).zfill(5)) if m else None


def hours_on(opening_hours: dict, day) -> tuple[str, str] | None:
    """A date's opening hours as (open, close), a dated line beating the weekday; None if closed."""
    value = opening_hours.get(day.isoformat()) or opening_hours.get(
        DAYS[day.weekday()], "closed"
    )
    return _span(value)


def site_now(conv) -> datetime:
    _, tz = site_timezone(conv)
    now = conv.state.datetime_now
    return now.astimezone(tz) if isinstance(now, datetime) else datetime.now(tz)


def next_opening(conv) -> str:
    """When the office next opens: 'today at 7', 'tomorrow at 7', 'on Monday at 8'. "" when the
    hours are blank or never open."""
    hours = site_opening_hours(conv)
    if not any(_span(v) for v in hours.values()):
        return ""
    now = site_now(conv)
    for ahead in range(0, 8):
        day = (now + timedelta(days=ahead)).date()
        span = hours_on(hours, day)
        if not span or (ahead == 0 and now.strftime("%H:%M") >= span[0]):
            continue
        when = (
            "today"
            if ahead == 0
            else "tomorrow"
            if ahead == 1
            else f"on {day.strftime('%A')}"
        )
        return f"{when} at {_clock(span[0])}"
    return ""


def day_hours_sentence(conv, day) -> str:
    """One day's hours as a short sentence: 'On Saturday we're open from 8 to 4.'"""
    hours = site_opening_hours(conv)
    span = hours_on(hours, day)
    now = site_now(conv).date()
    name = (
        "today"
        if day == now
        else "tomorrow"
        if day == now + timedelta(days=1)
        else f"on {day.strftime('%A')}"
    )
    if not span:
        return f"We're closed {name}."
    return f"{name[0].upper() + name[1:]} we're open from {_clock(span[0])} to {_clock(span[1])}."


@func_description("[UTIL] Site facts and opening hours helpers, not callable directly")
def utils(conv: Conversation):
    pass
