from _gen import *  # <AUTO GENERATED>
import re
from itertools import groupby
from zoneinfo import ZoneInfo


DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DEFAULT_TIMEZONE = "America/New_York"
_LINE = re.compile(
    r"^\s*([A-Za-z]+)\s*:\s*(closed|\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})\s*$", re.I
)


def variant_timezone(conv) -> str:
    """The variant's timezone attribute, if it's a valid zone; else the default."""
    name = (
        str(getattr(conv.variant, "timezone", "") or "").strip() if conv.variant else ""
    )
    try:
        ZoneInfo(name)
        return name
    except Exception:
        if name:
            conv.log.warning("Invalid timezone attribute", timezone=name)
        return DEFAULT_TIMEZONE


def parse_opening_hours(text: str) -> dict:
    """'Monday: 10:00-21:00' lines (one day per line, or 'closed') -> {'monday': '10:00-21:00'}.
    Lines that don't parse are ignored; days not listed are closed."""
    hours = {}
    for line in str(text or "").splitlines():
        match = _LINE.match(line)
        if match and match.group(1).lower() in DAYS:
            hours[match.group(1).lower()] = re.sub(r"\s+", "", match.group(2).lower())
    return hours


def variant_opening_hours(conv) -> dict:
    """The variant's opening_hours, parsed; {} when blank or unreadable."""
    return parse_opening_hours(
        getattr(conv.variant, "opening_hours", "") if conv.variant else ""
    )


def hours_not_to_hand(conv) -> str:
    """What the agent says when the variant has no readable hours. Never a guessed time;
    points to the website only when the variant has one."""
    website = (
        str(getattr(conv.variant, "website_url", "") or "").strip()
        if conv.variant
        else ""
    )
    if website:
        return (
            "I don't have our exact opening hours to hand, but they're on our website."
        )
    return "I don't have our exact opening hours to hand."


def _fmt_time(t: str) -> str:
    h, m = map(int, t.split(":"))
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


def opening_hours_utterance(opening_hours: dict) -> str:
    """{'monday': '10:00-21:00', ...} -> "We're open Monday through Saturday 10am to 9pm, and
    Sunday 11am to 6pm." Consecutive days with the same hours are grouped; closed days
    break a range. Returns '' when there are no hours."""
    schedule = [(d, opening_hours.get(d, "closed")) for d in DAYS]
    groups = []
    for hours, items in groupby(schedule, key=lambda x: x[1]):
        if hours.strip().lower() == "closed":
            continue
        groups.append(([d for d, _ in items], hours))
    if not groups:
        return ""
    parts = [f"{_fmt_day_range(days)} {_fmt_hours(hours)}" for days, hours in groups]
    if len(parts) == 1:
        return f"We're open {parts[0]}."
    return f"We're open {', '.join(parts[:-1])}, and {parts[-1]}."


@func_description("[UTIL] Opening hours helpers, not callable directly")
def utils(conv: Conversation):
    pass
