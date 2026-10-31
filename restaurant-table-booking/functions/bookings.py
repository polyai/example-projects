"""Booking rules, readbacks and the call-state block, shared by every task flow.

The flows stay one prompt and a few tools each because the rules live here:
- which time to offer: opening hours and last seating, no times in the past,
  room for the whole party, the nearest free time when the one asked for is
  taken, one offer at a time, nothing the caller has already turned down;
- the largest party the agent can book (settings.max_party_size);
- which upcoming booking the caller means;
- what the caller confirms before a write: one short yes-or-no question naming
  the action and the key details (ask_yes_no), and which details the caller has
  heard, so a later change is confirmed again (readback_text);
- the CALL STATE block every tool response ends with. On voice a step prompt is
  rendered once, when the step is entered, so state shown in the prompt would
  freeze; the latest tool response is always current.
"""

from _gen import *  # <AUTO GENERATED>
import re
from datetime import date, datetime, timedelta

import functions.api_client as api_client
import functions.hours as hours
import functions.idnv as idnv

DEFAULT_MAX_PARTY_SIZE = 8
MAX_REJECTED_OFFERS = 4  # offered times turned down before the caller is put through
BOOKING_NOTICE_MINUTES = 15  # a table today must start at least this far ahead

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}  # fmt: skip
_SAY_NUMBER = {v: k for k, v in _NUMBER_WORDS.items()}


@func_description("[UTIL] Booking rules and readback helpers, not callable directly")
def bookings(conv: Conversation):
    return "Booking helpers module."


# --- Settings ---------------------------------------------------------------


def setting(conv, key: str, default):
    """A switch from real-time config (`settings.<key>`), with the code default."""
    value = (conv.real_time_config or {}).get("settings", {}).get(key, default)
    return default if value is None else value


def max_party_size(conv) -> int:
    try:
        return int(setting(conv, "max_party_size", DEFAULT_MAX_PARTY_SIZE))
    except (TypeError, ValueError):
        return DEFAULT_MAX_PARTY_SIZE


# --- Today ------------------------------------------------------------------


def today(conv) -> date:
    """The restaurant's local date (start_function stores it as today_iso)."""
    try:
        return date.fromisoformat(conv.state.today_iso)
    except (TypeError, ValueError):
        return date.today()


def now(conv) -> datetime:
    try:
        return datetime.fromisoformat(conv.state.now_iso)
    except (TypeError, ValueError):
        return datetime.combine(today(conv), datetime.now().time())


# --- Parsing what the model passes ------------------------------------------


def parse_party(value) -> int:
    text = str(value or "").strip().lower()
    match = re.search(r"\d+", text)
    if match:
        return int(match.group())
    for word, n in _NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", text):
            return n
    return 0


def parse_date(conv, value) -> date | None:
    text = str(value or "").strip().lower()
    if not text or text in ("na", "none", "-"):
        return None
    if text in ("today", "tonight"):
        return today(conv)
    if text == "tomorrow":
        return today(conv) + timedelta(days=1)
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        conv.log.warning("Unparseable booking date", value=text)
        return None


def parse_time(value) -> str:
    """'19:00', '7pm', '7:30 pm', 'noon' -> 'HH:MM'; '' if not a time."""
    text = str(value or "").strip().lower().replace(".", "")
    if not text or text in ("na", "none", "-"):
        return ""
    if text in ("noon", "midday"):
        return "12:00"
    match = re.match(r"^(\d{1,2})(?::?(\d{2}))?\s*(am|pm)?$", text)
    if not match:
        return ""
    hour, minute, period = int(match.group(1)), int(match.group(2) or 0), match.group(3)
    if period == "pm" and hour < 12:
        hour += 12
    if period == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return ""
    return f"{hour:02d}:{minute:02d}"


# --- Saying things ----------------------------------------------------------


def _ordinal(n: int) -> str:
    suffix = (
        "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


def say_date(conv, day_iso: str) -> str:
    day = date.fromisoformat(day_iso)
    text = f"{day.strftime('%A')}, {day.strftime('%B')} {_ordinal(day.day)}"
    if day == today(conv):
        return f"today, {text}"
    if day == today(conv) + timedelta(days=1):
        return f"tomorrow, {text}"
    return text


def say_party(n: int) -> str:
    return f"{_SAY_NUMBER.get(int(n), str(n))} {'person' if int(n) == 1 else 'people'}"


def say_when(conv, day_iso: str, hhmm: str) -> str:
    return f"{say_date(conv, day_iso)} at {hours.say_time(hhmm)}"


def short_date(conv, day_iso: str) -> str:
    """The day as briefly as a yes-or-no question needs it: 'today', 'tomorrow',
    'Friday the 23rd' within two weeks, else 'Friday, November 13th'."""
    day = date.fromisoformat(day_iso)
    ahead = (day - today(conv)).days
    if ahead == 0:
        return "today"
    if ahead == 1:
        return "tomorrow"
    if 0 < ahead < 14:
        return f"{day.strftime('%A')} the {_ordinal(day.day)}"
    return f"{day.strftime('%A')}, {day.strftime('%B')} {_ordinal(day.day)}"


def short_when(conv, day_iso: str, hhmm: str) -> str:
    return f"{short_date(conv, day_iso)} at {hours.say_time(hhmm)}"


def short_table(conv, party_size, day_iso: str, hhmm: str) -> str:
    """'a table for four people tomorrow at 7pm': the item a write question names."""
    return f"a table for {say_party(party_size)} {short_when(conv, day_iso, hhmm)}"


def describe_booking(conv, booking: dict) -> str:
    text = (
        f"a table for {say_party(booking['party_size'])} "
        f"{say_when(conv, booking['date'], booking['time'])}"
    )
    if booking.get("notes"):
        text += f", with the note '{booking['notes']}'"
    return text


# --- Choosing a time --------------------------------------------------------


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def find_time(
    conv,
    day: date,
    wanted: str,
    party_size: int,
    declined: tuple | list = (),
    ignore_booking_id: str = "",
) -> tuple[str | None, str]:
    """The time to offer on `day`, and what to tell the caller about it.

    Returns (time, note). time is None when nothing can be offered that day;
    the note then says why and what to ask. When the time asked for is free the
    note is empty; otherwise it explains the nearest free time being offered.
    """
    if day < today(conv):
        return None, "That date has already passed. Ask which day they meant."
    shifts = hours.shifts_on(conv, day)
    if shifts == []:
        return None, (
            f"We're closed on {day.strftime('%A')}s. Say so and ask if another day would suit."
        )

    earliest = None
    if day == today(conv):
        earliest = now(conv) + timedelta(minutes=BOOKING_NOTICE_MINUTES)
        earliest = earliest.hour * 60 + earliest.minute
    free = [
        t
        for t in api_client.available_times(conv, day, party_size, ignore_booking_id)
        if hours.can_seat(conv, day, t)
        and (earliest is None or _minutes(t) >= earliest)
        and t not in declined
    ]

    # No am/pm: "seven" means 7pm when 7am can't be seated (restaurant hours).
    if wanted and _minutes(wanted) < 12 * 60 and not hours.can_seat(conv, day, wanted):
        later = f"{_minutes(wanted) // 60 + 12:02d}:{wanted[3:]}"
        if hours.can_seat(conv, day, later):
            wanted = later

    if wanted in free:
        return wanted, ""
    if not free:
        if declined:
            return None, (
                "There are no other times free that day. Say so and ask if another day would suit."
            )
        return None, (
            f"Nothing is free that day for {say_party(party_size)}. Say so and ask if another "
            "day would suit."
        )
    target = _minutes(wanted) if wanted else _minutes(free[0])
    nearest = min(free, key=lambda t: (abs(_minutes(t) - target), -_minutes(t)))
    if not wanted:
        return nearest, ""
    if not hours.can_seat(conv, day, wanted):
        why = f"we're open {hours.say_shifts(shifts or [])} that day"
        if shifts is None:  # unknown hours: the default window isn't ours to state
            why = "that time can't be booked; don't give opening hours"
    elif earliest is not None and _minutes(wanted) < earliest:
        why = "that time has passed"
    elif wanted in declined:
        why = "they turned it down"
    else:
        why = "it's fully booked"
    return nearest, (
        f"{hours.say_time(wanted)} isn't available ({why}); {hours.say_time(nearest)} is the "
        "nearest free time. Say so briefly."
    )


# --- Readbacks --------------------------------------------------------------


def readback_changes(conv, key: str, fields: list[tuple[str, str]]) -> tuple[dict, str]:
    """Like readback_text, but returns {label: value} for what the caller hasn't heard."""
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    last = store.get(key)
    current = {label: value for label, value in fields if value}
    conv.state.readbacks = {**store, key: current}
    if last is None:
        return current, "full"
    changed = {
        label: value for label, value in current.items() if last.get(label) != value
    }
    return changed, ("changes" if changed else "none")


def readback_text(conv, key: str, fields: list[tuple[str, str]]) -> tuple[str, str]:
    """What to read back for `key`: every field the first time, then only the
    fields whose value changed since the last readback.

    Returns (text, mode): mode is "full" the first time, "changes" when some
    fields changed, and "none" when the caller has already heard all of it, so
    a write tool can go ahead on a "yes".
    """
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    last = store.get(key)
    current = {label: value for label, value in fields if value}
    conv.state.readbacks = {**store, key: current}
    if last is None:
        return "; ".join(current.values()), "full"
    changed = [value for label, value in current.items() if last.get(label) != value]
    return "; ".join(changed), ("changes" if changed else "none")


def readback_is_current(conv, key: str, fields: list[tuple[str, str]]) -> bool:
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    current = {label: value for label, value in fields if value}
    return store.get(key) == current


def remember_readback(conv, key: str, fields: list[tuple[str, str]]) -> None:
    """Record that the caller has heard these values (e.g. an existing booking read out)."""
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    conv.state.readbacks = {
        **store,
        key: {label: value for label, value in fields if value},
    }


def forget_readback(conv, key: str) -> None:
    store = dict(conv.state.readbacks) if isinstance(conv.state.readbacks, dict) else {}
    store.pop(key, None)
    conv.state.readbacks = store


# --- Yes-or-no confirmations ---------------------------------------------------


def not_done_yet(question: str) -> dict:
    """A 'true' in the same turn as the question can't be the caller's answer. Speak
    the question (an utterance ends the tool loop: on RSN-1 a text refusal here let
    the model call the write again and again until the turn failed) and write nothing."""
    return {"utterance": f"{question}, yes or no?"}


def ask_yes_no(question: str, also_changed: str = "") -> str:
    """A write tool's confirmation: one short yes-or-no question naming the action and
    the key details, so a vague "okay" doesn't fit as an answer. The question is the
    readback, so nothing else is read back before it, except a changed detail the
    question doesn't name (also_changed)."""
    if also_changed:
        return (
            f"Say only what else changed ({also_changed}), then ask: '{question}, yes or no?' "
            "Wait for the answer."
        )
    return f"Ask just this, with no readback before it: '{question}, yes or no?' Wait for the answer."


def _turn(conv):
    """The history's length, used only as a same-turn marker: at tool time the
    history holds earlier turns, so it grows once the caller has replied. None if
    the platform doesn't expose it."""
    try:
        return len(conv.history)
    except Exception:
        return None


def mark_asked(conv, key: str) -> None:
    """Record the turn in which the yes-or-no question for `key` was asked."""
    store = conv.state.asked_turns if isinstance(conv.state.asked_turns, dict) else {}
    conv.state.asked_turns = {**store, key: _turn(conv)}


def asked_this_turn(conv, key: str) -> bool:
    """True while the caller hasn't replied since the question for `key` was asked,
    so a 'true' in the same turn can't be their answer."""
    store = conv.state.asked_turns if isinstance(conv.state.asked_turns, dict) else {}
    turn = _turn(conv)
    return turn is not None and key in store and store[key] == turn


def is_true(value) -> bool:
    return str(value or "").strip().lower() == "true"


# --- Existing bookings ------------------------------------------------------


def upcoming(conv) -> list[dict]:
    guest = idnv.customer(conv)
    if not guest:
        return []
    return api_client.list_bookings(conv, guest["id"])


def selected(conv) -> dict | None:
    wanted = conv.state.selected_booking_id
    return next((b for b in upcoming(conv) if b["id"] == wanted), None)


def select_for_task(conv, task: str) -> str:
    """Pick the booking a check / change / cancel is about and say what to do.

    One booking: it is selected. Several: the soonest is selected and the
    caller is asked if that's the one (a yes/no question), with the others
    named. None: no dead end; the caller is offered a new booking or the team.
    """
    conv.state.selected_booking_id = ""
    conv.state.booking_choice_unclear = 0
    found = upcoming(conv)
    if not found:
        conv.write_metric("NO_UPCOMING_BOOKING", task)
        return (
            "There are no upcoming bookings under this name and number. Tell the caller that, "
            "and ask if they'd like to make a new booking (if yes, call start_make_booking). If "
            "they're sure they have one, offer to put them through to the team (handoff with "
            "handoff_reason=NO_BOOKING_FOUND)."
        )
    if len(found) == 1:
        conv.state.selected_booking_id = found[0]["id"]
        return ""
    # Several: start with the soonest as a yes/no question, never an either/or one.
    conv.state.selected_booking_id = found[0]["id"]
    others = "; ".join(describe_booking(conv, b) for b in found[1:])
    return (
        f"The caller has {len(found)} upcoming bookings. Ask about the soonest one first, as "
        f"below, and mention they have {len(found) - 1} more ({others}). If they mean another one, "
        "call choose_booking with its date and time."
    )


def choose(conv, booking_date: str, booking_time: str) -> dict | None:
    """The one upcoming booking matching what the caller said, or None."""
    day = parse_date(conv, booking_date)
    hhmm = parse_time(booking_time)
    matches = [
        b
        for b in upcoming(conv)
        if (not day or b["date"] == day.isoformat()) and (not hhmm or b["time"] == hhmm)
    ]
    if (day or hhmm) and len(matches) == 1:
        conv.state.selected_booking_id = matches[0]["id"]
        return matches[0]
    return None


# --- Call state -------------------------------------------------------------


def call_state(conv, task_lines: list[str], next_line: str) -> str:
    lines = [
        "CALL STATE (this replaces any earlier copy; never read it aloud)",
        f"- {idnv.state_line(conv)}",
    ]
    lines += [f"- {line}" for line in task_lines if line]
    lines.append(f"NEXT: {next_line}")
    return "\n".join(lines)
