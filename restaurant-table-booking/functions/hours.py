"""Opening hours, read from the `opening_hours` variant attribute.

The attribute holds one line per day, as the onboarding scrape writes it:

    Monday: 12:00-21:00
    Tuesday: closed
    Friday: 12:00-15:00; 17:00-23:30
    Saturday: 17:00-01:00          (closes after midnight)

Everything that depends on the hours (is the restaurant open now, can a table
start at 8:45pm on Sunday, what to tell a caller who asks) is decided here.
If the attribute is empty or unreadable, the hours are unknown. The agent then
says it doesn't have them, the restaurant counts as open (never out of hours),
and only the booking check falls back to DEFAULT_SERVICE, so a table can't be
booked for 3am. The default is never spoken: it isn't the restaurant's hours.
"""

from datetime import date, datetime, timedelta

from _gen import *  # <AUTO GENERATED>

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
LAST_SEATING_MINUTES = 30  # the last table starts this long before closing
# Booking check only, when the hours are unknown: 11am-11pm every day (last table
# 10:30pm) covers brunch, lunch and dinner at nearly every full-service restaurant
# and refuses only times no restaurant would seat. Never said to the caller.
DEFAULT_SERVICE = [(11 * 60, 23 * 60)]


@func_description("[UTIL] Opening hours helpers, not callable directly")
def hours(conv: Conversation):
    return "Opening hours module."


def _minutes(hhmm: str) -> int:
    h, m = hhmm.strip().split(":")
    return int(h) * 60 + int(m)


def parse_opening_hours(text) -> dict[str, list[tuple[int, int]]]:
    """{'monday': [(open_min, close_min), ...]}; [] for a closed day. Days not
    listed are missing from the dict. A close at or before the open runs past
    midnight (close_min > 1440)."""
    parsed: dict[str, list[tuple[int, int]]] = {}
    for line in str(text or "").splitlines():
        if ":" not in line:
            continue
        day, _, value = line.partition(":")
        day = day.strip().lower()
        if day not in DAYS:
            continue
        value = value.strip().lower()
        if not value or value in ("closed", "close"):
            parsed[day] = []
            continue
        shifts = []
        for part in value.replace(",", ";").split(";"):
            if "-" not in part:
                continue
            start, _, end = part.partition("-")
            try:
                open_min, close_min = _minutes(start), _minutes(end)
            except ValueError:
                continue
            if close_min <= open_min:
                close_min += 24 * 60
            shifts.append((open_min, close_min))
        if shifts:
            parsed[day] = shifts
    return parsed


def opening_hours(conv) -> dict[str, list[tuple[int, int]]]:
    text = getattr(conv.variant, "opening_hours", "") if conv.variant else ""
    return parse_opening_hours(text)


def known(conv) -> bool:
    return bool(opening_hours(conv))


def shifts_on(conv, day: date) -> list[tuple[int, int]] | None:
    """The day's shifts, [] when closed, None when the hours aren't known."""
    table = opening_hours(conv)
    if not table:
        return None
    return table.get(DAYS[day.weekday()], [])


def is_open_at(conv, moment: datetime) -> bool:
    if not known(conv):
        return True
    minute = moment.hour * 60 + moment.minute
    for open_min, close_min in shifts_on(conv, moment.date()) or []:
        if open_min <= minute < close_min:
            return True
    yesterday = moment.date() - timedelta(days=1)
    for _open_min, close_min in shifts_on(conv, yesterday) or []:
        if close_min > 24 * 60 and minute < close_min - 24 * 60:
            return True
    return False


def say_open_now(conv, moment: datetime) -> str:
    """Open or closed at this moment, from the set hours only. "" when unknown."""
    if not known(conv):
        return ""
    minute = moment.hour * 60 + moment.minute
    today, yesterday = moment.date(), moment.date() - timedelta(days=1)
    closes = [c for o, c in shifts_on(conv, today) or [] if o <= minute < c]
    closes += [
        c - 24 * 60
        for _o, c in shifts_on(conv, yesterday) or []
        if minute < c - 24 * 60
    ]
    if closes:
        return f"We're open now until {_say_minutes(max(closes))}."
    for offset in range(8):
        day = today + timedelta(days=offset)
        starts = [o for o, _c in shifts_on(conv, day) or [] if offset or o > minute]
        if starts:
            when = (
                ["today", "tomorrow"][offset]
                if offset < 2
                else f"on {day.strftime('%A')}"
            )
            return f"We're closed right now; we open again at {_say_minutes(min(starts))} {when}."
    return "We're closed right now."


def can_seat(conv, day: date, hhmm: str) -> bool:
    """Can a table start at this time? Unknown hours use DEFAULT_SERVICE."""
    shifts = shifts_on(conv, day)
    if shifts is None:
        shifts = DEFAULT_SERVICE
    minute = _minutes(hhmm)
    return any(o <= minute <= c - LAST_SEATING_MINUTES for o, c in shifts)


def say_time(hhmm: str) -> str:
    minute = _minutes(hhmm) % (24 * 60)
    h, m = divmod(minute, 60)
    if (h, m) == (12, 0):
        return "noon"
    if (h, m) == (0, 0):
        return "midnight"
    suffix = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}{suffix}" if not m else f"{h12}:{m:02d}{suffix}"


def _say_minutes(minute: int) -> str:
    minute %= 24 * 60
    return say_time(f"{minute // 60:02d}:{minute % 60:02d}")


def say_shifts(shifts: list[tuple[int, int]]) -> str:
    if not shifts:
        return "closed"
    return " and ".join(f"{_say_minutes(o)} to {_say_minutes(c)}" for o, c in shifts)


def say_day(conv, day: date) -> str:
    shifts = shifts_on(conv, day)
    if shifts is None:
        return ""
    return f"{day.strftime('%A')}: {say_shifts(shifts)}"


def summary(conv) -> str:
    """The week in a sentence, grouping days with the same hours."""
    table = opening_hours(conv)
    if not table:
        return ""
    groups: list[tuple[list[str], str]] = []
    for day in DAYS:
        said = say_shifts(table[day]) if day in table else "hours not listed"
        if groups and groups[-1][1] == said:
            groups[-1][0].append(day)
        else:
            groups.append(([day], said))
    parts = []
    for days, said in groups:
        name = days[0].capitalize()
        if len(days) == 2:
            name += f" and {days[1].capitalize()}"
        elif len(days) > 2:
            name += f" to {days[-1].capitalize()}"
        parts.append(f"{name} {said}")
    return "; ".join(parts) + "."
