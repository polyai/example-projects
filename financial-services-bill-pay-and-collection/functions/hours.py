"""Opening hours and the local time, read from the variant.

Hours and timezone are variant attributes (`opening_hours`, `timezone`) so that
onboarding can write them per site. `opening_hours` has one line per day in the
form `Monday: 09:00-18:00` or `Sunday: closed`.

Whether out-of-hours handling is on at all is a switch in real-time config
(`flags.ooh_enabled`, default off; `flags.ooh_forced` forces it for testing).

Onboarding leaves `opening_hours` blank when it can't check the hours. Blank or
unreadable hours (no day with an open time) mean: the rules treat the contact
centre as open, so no caller is ever told we're closed on a guess, and what the
agent says is that it doesn't have the hours in front of it, never a made-up time.
A day that isn't listed is unknown, not closed: it is never treated as closed and
never said.
"""

from _gen import *  # <AUTO GENERATED>
import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = "America/New_York"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@func_description("[UTIL] Opening hours helpers, not callable directly")
def hours(conv: Conversation):
    return "Opening hours module."


def timezone(conv) -> ZoneInfo:
    name = (getattr(conv.variant, "timezone", "") or "").strip() if conv.variant else ""
    try:
        return ZoneInfo(name or DEFAULT_TIMEZONE)
    except Exception:
        conv.log.warning("Invalid timezone attribute, using default", timezone=name)
        return ZoneInfo(DEFAULT_TIMEZONE)


def now(conv) -> datetime:
    return datetime.now(timezone(conv))


def parse_opening_hours(text) -> dict[int, tuple[time, time] | None]:
    """{weekday: (open, close)}, or None for a day listed as closed. A day that isn't listed is
    left out: unknown, not closed."""
    out: dict[int, tuple[time, time] | None] = {}
    for line in str(text or "").splitlines():
        if ":" not in line:
            continue
        day, value = line.split(":", 1)
        day = day.strip().capitalize()
        if day not in DAYS:
            continue
        match = re.search(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", value)
        if not match:
            out[DAYS.index(day)] = None
            continue
        h1, m1, h2, m2 = (int(x) for x in match.groups())
        out[DAYS.index(day)] = (
            time(h1, m1),
            time(23, 59) if h2 == 24 else time(h2, m2),
        )
    return out


def opening_table(conv) -> dict[int, tuple[time, time] | None]:
    """The variant's hours, or {} when they're blank or unreadable (no day with an open time)."""
    table = parse_opening_hours(
        getattr(conv.variant, "opening_hours", "") if conv.variant else ""
    )
    return table if any(table.values()) else {}


def has_hours(conv) -> bool:
    return bool(opening_table(conv))


def is_open(conv, at: datetime | None = None) -> bool:
    table = opening_table(conv)
    if not table:
        return True  # blank or unreadable hours: never treat the caller as out of hours
    moment = at or now(conv)
    if moment.weekday() not in table:
        return True  # a day that isn't listed is unknown, never closed
    slot = table[moment.weekday()]
    return bool(slot) and slot[0] <= moment.time() < slot[1]


def next_open(conv, at: datetime | None = None) -> datetime | None:
    """When the contact centre next opens, from the listed days; None if no listed day opens."""
    table = opening_table(conv)
    moment = at or now(conv)
    for ahead in range(0, 8):
        day = moment + timedelta(days=ahead)
        slot = table.get(day.weekday())
        if not slot:
            continue
        opens = day.replace(
            hour=slot[0].hour, minute=slot[0].minute, second=0, microsecond=0
        )
        if opens > moment:
            return opens
    return None


def back_line(conv, at: datetime | None = None) -> str:
    """'They're back at 9 tomorrow morning.' for the closed-team line, or '' if unknown."""
    moment = at or now(conv)
    opens = next_open(conv, moment)
    if not opens:
        return ""
    clock = f"{opens.hour % 12 or 12}" + (
        f":{opens.minute:02d}" if opens.minute else ""
    )
    part = (
        "morning"
        if opens.hour < 12
        else ("afternoon" if opens.hour < 17 else "evening")
    )
    days = (opens.date() - moment.date()).days
    if days == 0:
        when = f"this {part}"
    elif days == 1:
        when = f"tomorrow {part}"
    else:
        when = f"on {opens.strftime('%A')} {part}"
    return f"They're back at {clock} {when}."


def is_out_of_hours(conv, at: datetime | None = None) -> bool:
    flags = (conv.real_time_config or {}).get("flags", {}) or {}
    if flags.get("ooh_forced"):
        return True
    if not flags.get("ooh_enabled"):
        return False
    return not is_open(conv, at)


def date_guide(today) -> str:
    """Dates the model needs to turn "Friday" or "next week" into YYYY-MM-DD."""
    days = [today + timedelta(days=n) for n in range(1, 9)]
    listing = ", ".join(
        f"{d.strftime('%A %B')} {d.day} = {d.isoformat()}" for d in days
    )
    return f"Today is {today.isoformat()}. Next 8 days: {listing}."


def _say_time(t: time) -> str:
    if t.hour == 12 and t.minute == 0:
        return "noon"
    suffix = "am" if t.hour < 12 else "pm"
    h = t.hour % 12 or 12
    return f"{h}{suffix}" if not t.minute else f"{h}:{t.minute:02d}{suffix}"


def not_to_hand(conv) -> str:
    """What the agent says instead of hours it doesn't have."""
    website = (
        (getattr(conv.variant, "website_url", "") or "").strip() if conv.variant else ""
    )
    line = "I'm sorry, I don't have our opening hours in front of me"
    if website:
        return f"{line}, but you'll find them on our website, {website}."
    return f"{line}, but you'll find them on our website."


def say_hours(conv) -> str:
    """'Monday to Friday, 9am to 6pm; closed Saturday and Sunday' from the variant.

    With blank or unreadable hours, the "not to hand" sentence instead.
    """
    table = opening_table(conv)
    if not table:
        return not_to_hand(conv)
    groups: list[list] = []
    for i, day in enumerate(DAYS):
        if i not in table:
            groups.append([[], "unknown"])  # never said, and never grouped across
            continue
        slot = table[i]
        if groups and groups[-1][1] == slot:
            groups[-1][0].append(day)
        else:
            groups.append([[day], slot])
    parts = []
    for days, slot in groups:
        if slot == "unknown":
            continue
        span = days[0] if len(days) == 1 else f"{days[0]} to {days[-1]}"
        if slot:
            parts.append(f"{span}, {_say_time(slot[0])} to {_say_time(slot[1])}")
        else:
            parts.append(
                f"closed {span}"
                if len(days) == 1
                else f"closed {days[0]} to {days[-1]}"
            )
    return "; ".join(parts)


def hours_line(conv) -> str:
    """The full sentence the agent says about our phone hours."""
    if not has_hours(conv):
        return not_to_hand(conv)
    return f"Our phone lines are open {say_hours(conv)}."
