"""Appointment rules, readbacks and the call-state block, shared by every task flow.

The flows stay one prompt and a few tools each because the rules live here:
- when the clinic is open (the opening_hours variant attribute) and so which
  slots can be offered: no same-day bookings, the caller's preferred day and
  time of day, one slot offered at a time, a cap on turned-down offers;
- which upcoming appointment the caller means;
- what the agent reads back: everything the first time, then only what changed
  (readback_text), and the turn the yes-or-no question was asked, so a write
  never goes ahead on a "yes" made in that same turn (asked_this_turn);
- the CALL STATE block every tool response ends with. On voice a step prompt is
  rendered once, when the step is entered, so state shown in the prompt would
  freeze; the latest tool response is always current.
"""

from _gen import *  # <AUTO GENERATED>
import re
from datetime import date, datetime, timedelta

import functions.api_client as api_client
import functions.idnv as idnv

MAX_REJECTED_OFFERS = 3
TIME_OF_DAY = {
    "morning": ("00:00", "12:00"),
    "afternoon": ("12:00", "23:59"),
    "any": ("00:00", "23:59"),
}
WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
# The rules (slots, out-of-hours) use this when the opening_hours attribute is
# blank or unreadable. It is never spoken: the agent says HOURS_NOT_TO_HAND instead.
DEFAULT_OPENING_HOURS = (
    "Monday: 08:00-17:00\nTuesday: 08:00-17:00\nWednesday: 08:00-17:00\n"
    "Thursday: 08:00-17:00\nFriday: 08:00-17:00\nSaturday: closed\nSunday: closed"
)
HOURS_NOT_TO_HAND = "I don't have our exact opening hours to hand"


@func_description(
    "[UTIL] Appointment rules and readback helpers, not callable directly"
)
def appointments(conv: Conversation):
    return "Appointment helpers module."


# --- Opening hours ------------------------------------------------------------


def parse_opening_hours(text: str) -> dict[int, tuple[str, str] | None]:
    """'Monday: 08:00-17:00' per line -> {0: ('08:00', '17:00'), ..., 6: None}.

    A day that is missing, 'closed' or unreadable is closed."""
    hours: dict[int, tuple[str, str] | None] = dict.fromkeys(range(7))
    for line in str(text or "").splitlines():
        if ":" not in line:
            continue
        day, value = line.split(":", 1)
        day = day.strip().lower()
        index = next(
            (i for i, name in enumerate(WEEKDAYS) if name.lower().startswith(day[:3])),
            None,
        )
        match = re.search(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", value)
        if index is None or not match or len(day) < 3:
            continue
        h1, m1, h2, m2 = match.groups()
        hours[index] = (f"{int(h1):02d}:{m1}", f"{int(h2):02d}:{m2}")
    return hours


def _hours_attribute(conv) -> str:
    return (getattr(conv.variant, "opening_hours", "") or "") if conv.variant else ""


def hours_known(conv) -> bool:
    """True when the opening_hours attribute gives at least one open day. When it
    doesn't, the rules use DEFAULT_OPENING_HOURS but nothing spoken may."""
    return any(parse_opening_hours(_hours_attribute(conv)).values())


def opening_hours(conv) -> dict[int, tuple[str, str] | None]:
    text = _hours_attribute(conv)
    hours = parse_opening_hours(text)
    if not any(hours.values()):
        if text:
            conv.log.warning(
                "opening_hours attribute unreadable; using the default hours"
            )
        hours = parse_opening_hours(DEFAULT_OPENING_HOURS)
    return hours


def open_weekdays(conv) -> set[int]:
    return {day for day, hours in opening_hours(conv).items() if hours}


def hours_for_day(conv, day: date) -> tuple[str, str] | None:
    return opening_hours(conv)[day.weekday()]


def is_open_at(conv, moment: datetime) -> bool:
    hours = opening_hours(conv)[moment.weekday()]
    return bool(hours) and hours[0] <= moment.strftime("%H:%M") < hours[1]


def say_opening_hours(conv) -> str:
    """'Monday to Friday, 8am to 5pm; closed Saturday and Sunday'.

    With the attribute blank or unreadable: HOURS_NOT_TO_HAND, plus the website
    if the website_url attribute is set. Never the default hours."""
    if not hours_known(conv):
        website = (
            (getattr(conv.variant, "website_url", "") or "").strip()
            if conv.variant
            else ""
        )
        if website:
            return f"{HOURS_NOT_TO_HAND}, but they're on our website, {website}"
        return HOURS_NOT_TO_HAND
    hours = opening_hours(conv)
    groups: list[list] = []
    for day in range(7):
        if groups and groups[-1][1] == hours[day]:
            groups[-1][0].append(day)
        else:
            groups.append([[day], hours[day]])
    parts = []
    for days, span in groups:
        names = WEEKDAYS[days[0]] + (
            f" to {WEEKDAYS[days[-1]]}" if len(days) > 2 else ""
        )
        if len(days) == 2:
            names = f"{WEEKDAYS[days[0]]} and {WEEKDAYS[days[1]]}"
        parts.append(
            f"{names}, {say_time(span[0])} to {say_time(span[1])}"
            if span
            else f"closed {names}"
        )
    return "; ".join(parts)


# --- Speaking dates and times ----------------------------------------------


def _ordinal(n: int) -> str:
    suffix = (
        "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


def say_date(iso: str, today_: date | None = None) -> str:
    day = date.fromisoformat(iso)
    text = f"{day.strftime('%A')}, {day.strftime('%B')} {_ordinal(day.day)}"
    if today_ and day == today_ + timedelta(days=1):
        return f"tomorrow, {text}"
    return text


def say_time(hhmm: str) -> str:
    hour, minute = (int(x) for x in hhmm.split(":"))
    if hour == 12 and minute == 0:
        return "noon"
    suffix = "am" if hour < 12 else "pm"
    hour12 = hour % 12 or 12
    return f"{hour12}{suffix}" if not minute else f"{hour12}:{minute:02d}{suffix}"


def say_slot(slot: dict, today_: date | None = None, provider: bool = True) -> str:
    when = f"{say_date(slot['date'], today_)} at {say_time(slot['start'])}"
    return f"{when} with {slot['provider']}" if provider else when


def today(conv) -> date:
    """The call's local date (start_function stores it as today_iso)."""
    try:
        return date.fromisoformat(conv.state.today_iso)
    except (TypeError, ValueError):
        return date.today()


# --- Choosing slots -----------------------------------------------------------


def parse_date(value: str, conv) -> date | None:
    text = (value or "").strip()
    if not text or text.lower() in ("na", "any", "none", "asap", "earliest"):
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        conv.log.warning("Unparseable preferred date", value=text)
        return None


def find_slot(
    conv,
    preferred_date: str,
    time_of_day: str,
    provider_id: str = "",
    after: dict | None = None,
) -> tuple[dict | None, str]:
    """The slot to offer next, and a note on any rule that changed the request.

    Rules: no same-day or past bookings; start from the caller's preferred day;
    keep to their time of day if they gave one; when `after` is set (the caller
    turned the last offer down) offer the next slot after it.
    """
    first_day = today(conv) + timedelta(days=1)
    wanted = parse_date(preferred_date, conv)
    notes = []
    if wanted and wanted <= today(conv):
        notes.append(
            "We can't book same-day appointments by phone; this is the earliest. Say so briefly."
        )
        wanted = first_day
    start = max(wanted or first_day, first_day)
    lo, hi = TIME_OF_DAY.get((time_of_day or "any").lower(), TIME_OF_DAY["any"])
    slots = api_client.open_slots(conv, start, provider_id)
    if after:
        slots = [
            s
            for s in slots
            if (s["date"], s["start"]) > (after["date"], after["start"])
        ]
    matching = [s for s in slots if lo <= s["start"] < hi]
    if matching:
        if wanted and matching[0]["date"] != wanted.isoformat() and not after:
            if hours_known(conv) and not hours_for_day(conv, wanted):
                notes.append("The clinic is closed that day; say this is the nearest.")
            else:
                notes.append("Nothing is open that day; say this is the nearest.")
        return matching[0], " ".join(notes)
    if slots:
        part = (time_of_day or "").lower()
        notes.append(f"No {part} slots are open; offer this instead.")
        return slots[0], " ".join(notes)
    return None, " ".join(notes)


# --- Upcoming appointments ----------------------------------------------------


def describe(appt: dict, conv) -> str:
    kind = (appt.get("type") or "appointment").lower()
    return f"your {kind} on {say_slot(appt, today(conv))}"


def upcoming(conv) -> list[dict]:
    patient = idnv.customer(conv)
    if not patient:
        return []
    return api_client.list_appointments(conv, patient["id"])


def selected(conv) -> dict | None:
    wanted = conv.state.selected_appointment_id
    return next((a for a in upcoming(conv) if a["id"] == wanted), None)


def select_for_task(conv, task: str) -> str:
    """Pick the appointment a confirm / reschedule / cancel is about and say what to do.

    One appointment: it is selected. Several: the caller is asked which. None:
    no dead end; the caller is offered a new booking.
    """
    conv.state.selected_appointment_id = ""
    appts = upcoming(conv)
    if not appts:
        conv.write_metric("NO_UPCOMING_APPOINTMENT", task)
        return (
            "There are no upcoming appointments on this record. Tell the caller that, and offer "
            "to book one (if they want one, call start_booking_flow)."
        )
    if len(appts) == 1:
        conv.state.selected_appointment_id = appts[0]["id"]
        return f"APPOINTMENT: {describe(appts[0], conv)}."
    listing = "; ".join(describe(a, conv) for a in appts)
    return (
        f"The caller has {len(appts)} upcoming appointments: {listing}. Ask which one they mean "
        "(unless they've already said), then call choose_appointment."
    )


def choose(conv, appointment_date: str, appointment_type: str) -> dict | None:
    wanted = parse_date(appointment_date, conv)
    kind = (appointment_type or "").strip().lower()
    matches = [
        a
        for a in upcoming(conv)
        if (not wanted or a["date"] == wanted.isoformat())
        and (not kind or kind in ("any", "na") or _type_matches(kind, a["type"]))
    ]
    if len(matches) == 1:
        conv.state.selected_appointment_id = matches[0]["id"]
        return matches[0]
    return None


def _letters(value: str) -> str:
    return re.sub(r"[^a-z]", "", (value or "").lower())


def normalise_type(value: str) -> str:
    """The appointment type as one of api_client.APPOINTMENT_TYPES ('sick visit' ->
    'Sick visit', 'follow up' -> 'Follow-up'), or '' when it isn't one of them. A
    format check only: the model picks the type from what the caller said."""
    key = _letters(value)
    return next(
        (t for t in api_client.APPOINTMENT_TYPES if key and _letters(t) == key), ""
    )


def _type_matches(said: str, kind: str) -> bool:
    return normalise_type(said) == kind


# --- Readbacks --------------------------------------------------------------


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


def forget_readback(conv, key: str) -> None:
    store = dict(conv.state.readbacks) if isinstance(conv.state.readbacks, dict) else {}
    store.pop(key, None)
    conv.state.readbacks = store
    turns = (
        dict(conv.state.readback_turns)
        if isinstance(conv.state.readback_turns, dict)
        else {}
    )
    turns.pop(key, None)
    conv.state.readback_turns = turns


# --- Same-turn marker ---------------------------------------------------------

NOT_DONE_YET = "NOT DONE YET: wait for the caller's answer to the yes-or-no question, then call again."


def ask_yes_no(question: str, lead: str = "Ask") -> str:
    """A write's confirmation: one spoken question naming the action and the item,
    with no separate readback before it. Short on voice, and still a question an
    "okay" doesn't answer."""
    return (
        f"{lead}, as one yes-or-no question, without reading the details out separately: "
        f'"{question}" Wait for the answer.'
    )


def history_turn(conv) -> int | None:
    """The history's length, used only as a same-turn marker: the history at tool
    time holds earlier turns, so it grows once the caller has replied. Never read
    for its content. None if the platform doesn't expose it."""
    try:
        return len(conv.history)
    except Exception:
        return None


def mark_question(conv, key: str) -> None:
    """Record the turn in which a tool had the agent ask its yes-or-no question."""
    turns = (
        dict(conv.state.readback_turns)
        if isinstance(conv.state.readback_turns, dict)
        else {}
    )
    turns[key] = history_turn(conv)
    conv.state.readback_turns = turns


def asked_this_turn(conv, key: str) -> bool:
    """True while the caller can't have answered the question yet (same turn)."""
    turns = (
        conv.state.readback_turns if isinstance(conv.state.readback_turns, dict) else {}
    )
    turn = history_turn(conv)
    return turn is not None and turns.get(key) == turn


# --- Call state -------------------------------------------------------------


def call_state(conv, task_lines: list[str], next_line: str) -> str:
    lines = [
        "CALL STATE (this replaces any earlier copy; never read it aloud)",
        f"- {idnv.state_line(conv)}",
    ]
    lines += [f"- {line}" for line in task_lines if line]
    lines.append(f"NEXT: {next_line}")
    return "\n".join(lines)
