from _gen import *  # <AUTO GENERATED>
import re
from datetime import datetime, timedelta
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
    Lines that don't parse are ignored. A day missing from the list is unknown, never closed:
    only a line that says 'closed' is closed."""
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
    """What the agent says when it has no hours for the day asked about. Never a guessed time;
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


def _hm(t: str) -> tuple[int, int]:
    h, m = map(int, t.split(":"))
    return h, m


def fmt_time(t: str) -> str:
    """'21:00' -> '9pm', '10:30' -> '10:30am'."""
    h, m = _hm(t)
    period = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}{period}" if m else f"{h12}{period}"


def _fmt_hours(hours: str) -> str:
    start, end = hours.split("-")
    return f"{fmt_time(start)} to {fmt_time(end)}"


def spoken_time(t: str, when: str) -> str:
    """'10:00', 'tomorrow' -> '10 tomorrow morning'; '21:00', 'today' -> '9 tonight'."""
    h, m = _hm(t)
    clock = f"{h % 12 or 12}" + (f":{m:02d}" if m else "")
    part = "morning" if h < 12 else "afternoon" if h < 17 else "evening"
    if when == "today":
        return f"{clock} tonight" if part == "evening" else f"{clock} this {part}"
    if when == "tomorrow":
        return f"{clock} tomorrow {'night' if part == 'evening' else part}"
    return f"{clock} on {when} {part}"


def now_local(conv) -> datetime:
    timezone = ZoneInfo(variant_timezone(conv))
    return (conv.state.datetime_now or datetime.now(timezone)).astimezone(timezone)


def next_opening(conv, hours: dict) -> str:
    """When the store next opens, said for a caller ('10 tomorrow morning'), or '' when the
    hours don't say."""
    now = now_local(conv)
    for offset in range(0, 8):
        day = now + timedelta(days=offset)
        span = hours.get(DAYS[day.weekday()])
        if span is None:
            return ""  # a day we don't know: don't guess past it
        if span == "closed":
            continue
        start = span.split("-")[0]
        h, m = _hm(start)
        if offset == 0 and (now.hour, now.minute) >= (h, m):
            continue
        when = (
            "today"
            if offset == 0
            else "tomorrow"
            if offset == 1
            else day.strftime("%A")
        )
        return spoken_time(start, when)
    return ""


def opening_hours_utterance(opening_hours: dict) -> str:
    """{'monday': '10:00-21:00', ...} -> "Monday through Saturday 10am to 9pm, and Sunday 11am
    to 6pm." Consecutive days with the same hours are grouped; closed days and days not
    listed break a range and are left out. Returns '' when there are no hours."""
    schedule = [(d, opening_hours.get(d, "unknown")) for d in DAYS]
    groups = []
    for hours, items in groupby(schedule, key=lambda x: x[1]):
        if hours in ("closed", "unknown"):
            continue
        groups.append(([d for d, _ in items], hours))
    if not groups:
        return ""
    parts = [
        f"{days[0].capitalize()}"
        + (f" through {days[-1].capitalize()}" if len(days) > 1 else "")
        + f" {_fmt_hours(hours)}"
        for days, hours in groups
    ]
    if len(parts) == 1:
        return f"{parts[0]}."
    return f"{', '.join(parts[:-1])}, and {parts[-1]}."


def day_hours(opening_hours: dict, day: str) -> str:
    """'10am to 9pm', 'closed', or 'not listed' for one day."""
    span = opening_hours.get(day)
    if span is None:
        return "not listed"
    if span == "closed":
        return "closed"
    return _fmt_hours(span)


@func_description("[UTIL] Opening hours helpers, not callable directly")
def utils(conv: Conversation):
    pass
