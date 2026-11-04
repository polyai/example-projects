"""Appointment rules, availability, readbacks and spoken lines, shared by every task flow.

The flows stay one prompt and a few tools each because the rules live here:
- when the clinic is open (the opening_hours variant attribute; blank hours are
  never spoken and never make the clinic "closed");
- availability: the free times the EHR gives around a request (a day, a time
  that day, or the earliest), the nearest days either side of a day with
  nothing, no same-day or past bookings, closed days and a 21-day horizon. Code
  never filters by what the caller prefers or picks which times to offer;
- readbacks: the fields a write reads back, only what changed after a
  correction, and the turn the question was asked in, so a write never goes
  ahead on a yes in that same turn (asked_this_turn);
- the lines the design holds in code (done lines, the same-turn refusal, the
  caller-ID question and the ID&V lines).
"""

from _gen import *  # <AUTO GENERATED>
import re
from datetime import date, datetime, timedelta

import functions.api_client as api_client
import functions.idnv as idnv

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
# The rules (slots, out of hours) use this when the opening_hours attribute is
# blank or unreadable. It is never spoken, and blank hours never mean closed.
DEFAULT_OPENING_HOURS = (
    "Monday: 08:00-17:00\nTuesday: 08:00-17:00\nWednesday: 08:00-17:00\n"
    "Thursday: 08:00-17:00\nFriday: 08:00-17:00\nSaturday: closed\nSunday: closed"
)
HOURS_NOT_TO_HAND = "I'm sorry, I don't have our opening hours in front of me"
HORIZON_DAYS = 21  # how far ahead appointments can be booked by phone
NEAREST_DAYS = 7  # how far either side of a full day to look for the nearest free day
EARLIEST_DAYS = 2  # an "earliest" search returns the free times on this many days

# --- Lines held in code -------------------------------------------------------

CALLER_ID_QUESTION = "Is the number you're calling from the one on your patient record?"
# idnv's strict miss (attempt 1 of 2) says this, in place of its "account" wording.
MISMATCH_LINE = (
    "I'm sorry, those details don't match what we have. Could you say the phone number on "
    "your record again for me, or is it under a different one?"
)
ANYTHING_ELSE = "Is there anything else I can help with?"
CONSENT_HINT = 'A yes, or an acknowledgement ("okay", "sure", "sounds good") to that question is agreement.'


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


def _attr(conv, name: str) -> str:
    return str((getattr(conv.variant, name, "") or "") if conv.variant else "").strip()


def hours_known(conv) -> bool:
    """True when the opening_hours attribute gives at least one open day. When it
    doesn't, the rules use DEFAULT_OPENING_HOURS but nothing spoken may."""
    return any(parse_opening_hours(_attr(conv, "opening_hours")).values())


def opening_hours(conv) -> dict[int, tuple[str, str] | None]:
    text = _attr(conv, "opening_hours")
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
    """Open at this moment. Always True with blank hours: they never mean closed."""
    if not hours_known(conv):
        return True
    hours = opening_hours(conv)[moment.weekday()]
    return bool(hours) and hours[0] <= moment.strftime("%H:%M") < hours[1]


def spoken_website(conv) -> str:
    """'www.example-clinic.com' -> 'example-clinic dot com'."""
    site = re.sub(r"^https?://", "", _attr(conv, "website_url"), flags=re.I)
    site = re.sub(r"^www\.", "", site, flags=re.I).rstrip("/")
    return site.replace(".", " dot ")


def hours_not_to_hand(conv) -> str:
    site = spoken_website(conv)
    return (
        f"{HOURS_NOT_TO_HAND}, but they're on our website, {site}"
        if site
        else HOURS_NOT_TO_HAND
    )


def say_opening_hours(conv) -> str:
    """'Monday to Friday, 8am to 5pm, and closed at the weekend'. With the
    attribute blank or unreadable: the not-to-hand line. Never the default hours."""
    if not hours_known(conv):
        return hours_not_to_hand(conv)
    hours = opening_hours(conv)
    groups: list[list] = []
    for day in range(7):
        if groups and groups[-1][1] == hours[day]:
            groups[-1][0].append(day)
        else:
            groups.append([[day], hours[day]])
    parts = []
    for days, span in groups:
        if days == [5, 6] and not span:
            parts.append("closed at the weekend")
            continue
        names = WEEKDAYS[days[0]]
        if len(days) == 2:
            names = f"{WEEKDAYS[days[0]]} and {WEEKDAYS[days[1]]}"
        elif len(days) > 2:
            names = f"{WEEKDAYS[days[0]]} to {WEEKDAYS[days[-1]]}"
        parts.append(
            f"{names}, {say_time(span[0])} to {say_time(span[1])}"
            if span
            else f"closed {names}"
        )
    return ", and ".join(parts) if len(parts) == 2 else "; ".join(parts)


def say_hours_today(conv, now: datetime) -> str:
    """Today's hours as a sentence, for the hours topic."""
    if not hours_known(conv):
        return hours_not_to_hand(conv) + "."
    span = opening_hours(conv)[now.weekday()]
    if not span:
        when, opens = next_open(conv, now)
        return f"We're closed today. We're open again {when} from {say_time(opens)}."
    return f"Today we're open from {say_time(span[0])} to {say_time(span[1])}."


def say_open_now(conv, now: datetime) -> str:
    if not hours_known(conv):
        return hours_not_to_hand(conv) + "."
    span = opening_hours(conv)[now.weekday()]
    if span and is_open_at(conv, now):
        return f"We're open now, until {say_time(span[1])} today."
    when, opens = next_open(conv, now)
    return f"We're closed right now. We're open again {when} from {say_time(opens)}."


def next_open(conv, now: datetime) -> tuple[str, str]:
    """When we next open: ('today', '08:00'), ('tomorrow', '08:00') or ('on Monday', '08:00')."""
    hours = opening_hours(conv)
    today_span = hours[now.weekday()]
    if today_span and now.strftime("%H:%M") < today_span[0]:
        return "today", today_span[0]
    for offset in range(1, 8):
        day = now.date() + timedelta(days=offset)
        span = hours[day.weekday()]
        if span:
            return (
                "tomorrow" if offset == 1 else f"on {WEEKDAYS[day.weekday()]}"
            ), span[0]
    return "tomorrow", "08:00"


# --- Speaking dates and times ----------------------------------------------


def _ordinal(n: int) -> str:
    suffix = (
        "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


def say_date(iso: str, today_: date) -> str:
    """'today', 'tomorrow, Tuesday the 3rd', 'Thursday the 5th' within two weeks,
    then 'Monday, December 14th'. Never the year."""
    day = date.fromisoformat(iso)
    weekday = day.strftime("%A")
    if day == today_:
        return "today"
    if day == today_ + timedelta(days=1):
        return f"tomorrow, {weekday} the {_ordinal(day.day)}"
    if day - today_ <= timedelta(days=14):
        return f"{weekday} the {_ordinal(day.day)}"
    return f"{weekday}, {day.strftime('%B')} {_ordinal(day.day)}"


def short_date(iso: str, today_: date) -> str:
    """The date after its first mention: 'tomorrow', 'Thursday the 5th'."""
    day = date.fromisoformat(iso)
    if day == today_ + timedelta(days=1):
        return "tomorrow"
    return say_date(iso, today_)


def on_date(iso: str, today_: date) -> str:
    """'tomorrow' or 'on Thursday the 5th', for done lines and readbacks."""
    said = short_date(iso, today_)
    return said if said in ("today", "tomorrow") else f"on {said}"


def say_time(hhmm: str) -> str:
    hour, minute = (int(x) for x in hhmm.split(":"))
    if hour == 12 and minute == 0:
        return "noon"
    suffix = "am" if hour < 12 else "pm"
    hour12 = hour % 12 or 12
    return f"{hour12}{suffix}" if not minute else f"{hour12}:{minute:02d}{suffix}"


def today(conv) -> date:
    """The call's local date (start_function stores it as today_iso)."""
    try:
        return date.fromisoformat(conv.state.today_iso)
    except (TypeError, ValueError):
        from functions.start_function import local_now

        return local_now(conv)[1].date()


# --- Appointment types --------------------------------------------------------


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


def kind(appt_type: str) -> str:
    return (appt_type or "appointment").lower()


# --- Availability -------------------------------------------------------------


def slot_key(slot: dict) -> str:
    return f"{slot['date']} {slot['start']}"


def parse_slot(value: str) -> tuple[str, str] | None:
    """'2026-11-05 15:30' (or with a T) -> ('2026-11-05', '15:30'); None if not that shape."""
    match = re.match(r"^\s*(\d{4}-\d{2}-\d{2})[ T]+(\d{1,2}):(\d{2})", str(value or ""))
    if not match:
        return None
    try:
        day = date.fromisoformat(match.group(1))
    except ValueError:
        return None
    hour, minute = int(match.group(2)), int(match.group(3))
    if hour > 23 or minute > 59:
        return None
    return day.isoformat(), f"{hour:02d}:{minute:02d}"


def _parse_time(value: str) -> str | None:
    """'14:00' -> '14:00'; '' -> ''; anything else -> None."""
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.match(r"^(\d{1,2}):(\d{2})$", text)
    if not match or int(match.group(1)) > 23 or int(match.group(2)) > 59:
        return None
    return f"{int(match.group(1)):02d}:{match.group(2)}"


EARLIEST_WORDS = ("earliest", "any", "asap", "soonest", "first available")


def _said_weekday(day_said: str) -> int | None:
    words = re.findall(r"[a-z]+", str(day_said or "").lower())
    found = {i for i, name in enumerate(WEEKDAYS) if name.lower() in words}
    return found.pop() if len(found) == 1 else None


def _times(slots: list[dict]) -> str:
    return ", ".join(f"{say_time(s['start'])} [{slot_key(s)}]" for s in slots)


def _day_slots(conv, provider_id: str, day: date) -> list[dict]:
    return api_client.open_slots(conv, day, provider_id, days=1)


def _nearest(conv, provider_id: str, day: date, step: int) -> list[dict]:
    """The free times on the nearest day before (step -1) or after (step 1), within
    NEAREST_DAYS, never today or earlier."""
    for offset in range(1, NEAREST_DAYS + 1):
        other = day + timedelta(days=offset * step)
        if other <= today(conv):
            return []
        slots = _day_slots(conv, provider_id, other)
        if slots:
            return slots
    return []


def availability(
    conv,
    provider_id: str,
    preferred_date: str,
    preferred_time: str,
    day_said: str,
    question: str,
    handoff_reason: str,
    walk_ins: bool = False,
) -> dict:
    """The free times around a request, and what to tell the caller.

    Returns {"text": the tool return, "slots": every slot returned (the write
    takes only one of these), "offer": the one slot the offer names when it is
    also the readback (the requested time is free, or the earliest), else None}.
    `question` is the consent question an offer of one slot ends with; `walk_ins`
    says whether walk-ins may be mentioned for a same-day request (sick visits).
    """
    out = {"text": "", "slots": [], "offer": None}
    first_day = today(conv) + timedelta(days=1)
    wanted_text = str(preferred_date or "").strip().lower()
    wanted_time = _parse_time(preferred_time)
    if wanted_time is None:
        out["text"] = (
            "NOT CHECKED: pass preferred_time as HH:MM in 24-hour time (2pm is 14:00), or empty "
            "for any time. Then call again."
        )
        return out
    doctor = api_client.providers(conv)[api_client._provider_id(conv, provider_id)]
    # "The earliest" in the caller's words is the earliest, whatever date the model passed.
    said_earliest = re.search(
        r"earliest|soonest|as soon as|asap|first available", str(day_said or ""), re.I
    )

    if not wanted_text or wanted_text in EARLIEST_WORDS or said_earliest:
        slots = api_client.open_slots(conv, first_day, provider_id, days=HORIZON_DAYS)
        if not slots:
            out["text"] = (
                f"NOTHING FREE with {doctor} in the next three weeks. Say: \"I'm sorry, I can't "
                f"see anything free with {doctor} in the next three weeks. Our scheduling team "
                f'may be able to help. Shall I put you through?" If they agree, call handoff '
                f'with reason="{handoff_reason}".'
            )
            return out
        days = sorted({s["date"] for s in slots})[:EARLIEST_DAYS]
        returned = [s for s in slots if s["date"] in days]
        first = returned[0]
        others = "; ".join(
            f"{say_date(d, today(conv))}: {_times([s for s in returned[1:] if s['date'] == d])}"
            for d in days
            if [s for s in returned[1:] if s["date"] == d]
        )
        out.update(slots=returned, offer=first)
        out["text"] = (
            f"EARLIEST: {say_date(first['date'], today(conv))}, at {say_time(first['start'])} "
            f"with {doctor} [{slot_key(first)}]. Offer just that one time, no others, as "
            f'"The earliest I\'ve got is …", naming the doctor, day and time, and ask '
            f'"{question}" Other free times, only if the caller wants something '
            f"else: {others}."
        )
        return out

    try:
        wanted = date.fromisoformat(wanted_text[:10])
    except ValueError:
        out["text"] = (
            "NOT CHECKED: pass preferred_date as YYYY-MM-DD from the date guide, or 'earliest'. "
            "Then call again."
        )
        return out
    said = _said_weekday(day_said)
    if (
        said is not None
        and wanted == today(conv)
        and "today" not in str(day_said).lower()
    ):
        # A weekday alone is the next one after today: "Monday", said on a Monday, is next week's.
        wanted += timedelta(days=7)
    if said is not None and said != wanted.weekday():
        out["text"] = (
            f"NOT CHECKED: {wanted.isoformat()} is a {WEEKDAYS[wanted.weekday()]}, but the caller "
            f'said "{day_said}". Work the date out again from the date guide and call again; if '
            "it's still unclear, ask which date they mean."
        )
        return out
    if wanted < today(conv):
        out["text"] = "NOT CHECKED: that date has passed. Ask which day they mean."
        return out
    if wanted == today(conv):
        earliest = api_client.open_slots(
            conv, first_day, provider_id, days=HORIZON_DAYS
        )[:1]
        out.update(slots=earliest)
        line = (
            "SAME DAY: we can't book same-day appointments over the phone. Say: \"We can't book "
            "same-day appointments over the phone, I'm afraid.\""
        )
        if earliest:
            e = earliest[0]
            line += (
                f" The earliest from tomorrow is {say_date(e['date'], today(conv))} at "
                f"{say_time(e['start'])} with {doctor} [{slot_key(e)}]."
            )
        walk_in = _attr(conv, "walk_in_info")
        if walk_in and walk_ins:
            line += (
                f" Walk-ins: {walk_in} Offer walk-ins or that earliest time, and ask which they'd "
                "prefer."
            )
        else:
            line += " Offer that earliest time."
        out["text"] = line
        return out
    if wanted > today(conv) + timedelta(days=HORIZON_DAYS):
        out["text"] = (
            "TOO FAR AHEAD: appointments can be booked up to three weeks ahead by phone. Say so, "
            "and ask for a day in the next three weeks, or offer the earliest."
        )
        return out
    if hours_known(conv) and not hours_for_day(conv, wanted):
        name = WEEKDAYS[wanted.weekday()]
        conv.write_metric("CLOSED_DAY_REQUESTED", name)
        out["text"] = (
            f"CLOSED: we're closed on {name}s. Say: \"We're closed on {name}s, I'm afraid. "
            'Would another day work for you?"'
        )
        return out

    day_said_out = say_date(wanted.isoformat(), today(conv))
    on_day = (
        day_said_out if day_said_out.startswith("tomorrow") else f"on {day_said_out}"
    )
    slots = _day_slots(conv, provider_id, wanted)
    if wanted_time:
        free = next((s for s in slots if s["start"] == wanted_time), None)
        if free:
            out.update(slots=[free], offer=free)
            out["text"] = (
                f"FREE: {doctor} has {say_time(wanted_time)} free {on_day} "
                f'[{slot_key(free)}]. Say just that, with no other times, and ask "{question}"'
            )
            return out
        if slots:
            out.update(slots=slots)
            out["text"] = (
                f"NOT FREE: {doctor} is fully booked at {say_time(wanted_time)} {on_day}. "
                f"Free that day: {_times(slots)}. Say {doctor}'s fully booked "
                "at that time, then offer the one or two of these that best fit what the caller "
                'said, never one they turned down and never more than two (one if only one fits: "after 3" means later than 3pm), and ask "Would either of those work?"'
            )
            return out
    elif slots:
        out.update(slots=slots)
        out["text"] = (
            f"FREE ON {day_said_out} with {doctor}: {_times(slots)}. Offer the one or two that "
            'best fit what the caller said, never one they turned down and never more than two (one if only one fits: "after 3" means later than 3pm), and ask "Would either of those work?"'
        )
        return out

    before = _nearest(conv, provider_id, wanted, -1)
    after = _nearest(conv, provider_id, wanted, 1)
    out.update(slots=before + after)
    near = "; ".join(
        f"{say_date(group[0]['date'], today(conv))}: {_times(group)}"
        for group in (before, after)
        if group
    )
    if not near:
        out["text"] = (
            f"FULLY BOOKED: {doctor} has nothing free {on_day}, or in the week either "
            "side. Say so, and ask if another day would work, or offer the earliest."
        )
        return out
    out["text"] = (
        f"FULLY BOOKED: {doctor} has nothing free {on_day}. Nearest: {near}. Say "
        f"{doctor}'s fully booked on {WEEKDAYS[wanted.weekday()]}, and offer one time from the "
        "nearest day before and one from the nearest day after (or one, if there's only one), "
        'and ask "Would either of those work?"'
    )
    return out


def slot_is_free(conv, provider_id: str, day: str, start: str) -> bool:
    slots = _day_slots(conv, provider_id, date.fromisoformat(day))
    return any(s["start"] == start for s in slots)


# --- Readbacks --------------------------------------------------------------


def history_turn(conv) -> int | None:
    """The history's length, used only as a same-turn marker: the history at tool
    time holds earlier turns, so it grows once the caller has replied. Never read
    for its content. None if the platform doesn't expose it."""
    try:
        return len(conv.history)
    except Exception:
        return None


def _readbacks(conv) -> dict:
    return dict(conv.state.readbacks) if isinstance(conv.state.readbacks, dict) else {}


def readback(conv, key: str) -> dict | None:
    """What was last read back for `key`: {"item": ..., "fields": {...}, "turn": n}."""
    return _readbacks(conv).get(key)


def mark_readback(conv, key: str, item: str, fields: dict, offer: bool = False) -> dict:
    """Record what the caller is hearing for `key` and the turn they hear it in.
    Returns the fields that changed since the last readback: all of them the first
    time, or after an offer (an offer the caller turned down isn't a readback to
    correct). `offer` marks an offer that named everything and asked to go ahead."""
    store = _readbacks(conv)
    last = store.get(key) or {}
    before = {} if last.get("offer") else (last.get("fields") or {})
    changed = (
        {k: v for k, v in fields.items() if before.get(k) != v}
        if before
        else dict(fields)
    )
    store[key] = {
        "item": item,
        "fields": dict(fields),
        "turn": history_turn(conv),
        "offer": offer,
    }
    conv.state.readbacks = store
    return changed


def remark_turn(conv, key: str) -> None:
    """The question is being asked again: the yes must come in a later turn."""
    store = _readbacks(conv)
    if key in store:
        store[key] = {**store[key], "turn": history_turn(conv)}
        conv.state.readbacks = store


def readback_is_current(conv, key: str, item: str) -> bool:
    return (readback(conv, key) or {}).get("item") == item


def asked_this_turn(conv, key: str) -> bool:
    """True while the caller can't have answered the question yet (same turn)."""
    turn = history_turn(conv)
    return turn is not None and (readback(conv, key) or {}).get("turn") == turn


def forget_readback(conv, key: str) -> None:
    store = _readbacks(conv)
    store.pop(key, None)
    conv.state.readbacks = store


def readback_fields(
    slot: dict, appt_type: str, today_: date, doctor: bool = True
) -> dict:
    fields = {"type": kind(appt_type)}
    if doctor:
        fields["doctor"] = slot["provider"]
    fields["day"] = short_date(slot["date"], today_)
    fields["time"] = say_time(slot["start"])
    return fields


def read_back_text(fields: dict, changed: dict) -> str:
    """The fields to read back: all of them, or only those that changed."""
    labels = {
        "type": "the type",
        "doctor": "the doctor",
        "day": "the day",
        "time": "the time",
    }
    use = changed if changed and changed != fields else fields
    listing = ", ".join(f"{labels[k]} {v}" for k, v in use.items())
    if use is fields:
        return f"read back, in one sentence, {listing}"
    return f"read back only what changed, {listing}"


def readback_sentence(fields: dict, action: str) -> str:
    """The readback as one sentence, for the same-turn refusal (held in code).
    'So that's your follow-up with Dr. Smith on Thursday the 5th at 3:30pm.'"""
    day = (
        fields["day"]
        if fields["day"] in ("today", "tomorrow")
        else f"on {fields['day']}"
    )
    if action == "move":
        return f"So that's your {fields['type']} moved to {fields['day']} at {fields['time']}."
    if action == "cancel":
        return f"You've got a {fields['type']} with {fields['doctor']} {day} at {fields['time']}."
    return f"So that's your {fields['type']} with {fields['doctor']} {day} at {fields['time']}."


CONFIRM_QUESTIONS = {
    "book": "Shall I book that?",
    "move": "Shall I move it?",
    "cancel": "Shall I cancel that for you?",
}


def not_done_yet(fields: dict, action: str) -> dict:
    """The same-turn refusal: a yes in the turn the readback was asked can't be the
    caller's answer. Spoken in code, so the model can't call the write again in a
    loop: the readback and the question again."""
    return {
        "utterance": f"{readback_sentence(fields, action)} {CONFIRM_QUESTIONS[action]}"
    }


# --- Upcoming appointments ----------------------------------------------------


def describe(appt: dict, conv, doctor: bool = True) -> str:
    """'a follow-up with Dr. Smith on Thursday the 5th at 10am'."""
    who = f" with {appt['provider']}" if doctor else ""
    return (
        f"a {kind(appt.get('type'))}{who} {on_date(appt['date'], today(conv))} at "
        f"{say_time(appt['start'])}"
    )


def upcoming(conv) -> list[dict]:
    patient = idnv.customer(conv)
    if not patient:
        return []
    return api_client.list_appointments(conv, patient["id"])


def selected(conv) -> dict | None:
    wanted = conv.state.selected_appointment_id
    return next((a for a in upcoming(conv) if a["id"] == wanted), None)


def select_for_task(conv, task: str) -> str:
    """Pick the appointment a check / move / cancel is about and say what to do.

    One: it is selected. Two: both are named and the caller is asked which.
    Three or more: the soonest, and how many others. None: a new booking is offered.
    """
    conv.state.selected_appointment_id = ""
    appts = upcoming(conv)
    if not appts:
        conv.write_metric("NO_UPCOMING_APPOINTMENT", task)
        return (
            "NO UPCOMING APPOINTMENTS on this record. Say: \"I can't see any upcoming "
            'appointments for you. Would you like to book one?" If they do, call '
            "start_booking_flow."
        )
    if len(appts) == 1:
        conv.state.selected_appointment_id = appts[0]["id"]
        return f"APPOINTMENT: {describe(appts[0], conv)}."
    if len(appts) == 2:
        a, b = appts
        return (
            f"TWO APPOINTMENTS: {describe(a, conv)} and {describe(b, conv)}. Name both by type "
            f'and day ("I can see two appointments: a {kind(a["type"])} '
            f"{on_date(a['date'], today(conv))} and a {kind(b['type'])} "
            f'{on_date(b["date"], today(conv))}. Which one is it about?"), then call '
            "choose_appointment with the one they mean."
        )
    first = appts[0]
    return (
        f"{len(appts)} APPOINTMENTS. The soonest is {describe(first, conv)}, with "
        f"{len(appts) - 1} more after it. Ask about the soonest and say how many others there "
        f'are ("Your next one is a {kind(first["type"])} {on_date(first["date"], today(conv))}, '
        f"and you've got {len(appts) - 1} more after that. Is it that one?\"), then call "
        "choose_appointment with the one they mean."
    )


def choose(conv, appointment_date: str, appointment_type: str) -> dict | None:
    text = str(appointment_date or "").strip()
    try:
        wanted = date.fromisoformat(text[:10]) if text else None
    except ValueError:
        wanted = None
    want_kind = normalise_type(appointment_type)
    matches = [
        a
        for a in upcoming(conv)
        if (not wanted or a["date"] == wanted.isoformat())
        and (not want_kind or a["type"] == want_kind)
    ]
    if len(matches) == 1 and (wanted or want_kind):
        conv.state.selected_appointment_id = matches[0]["id"]
        return matches[0]
    return None


# --- The cancel readback (entry step and choose_appointment) ------------------


def cancel_fields(conv, appt: dict) -> dict:
    return readback_fields(appt, appt.get("type"), today(conv))


def cancel_readback(conv) -> str:
    appt = selected(conv)
    if not appt:
        return "First find out which appointment they want to cancel."
    mark_readback(conv, "cancel", appt["id"], cancel_fields(conv, appt))
    return (
        f'APPOINTMENT: {describe(appt, conv)}. Say it and ask "Shall I cancel that for you?" '
        f'("You\'ve got {describe(appt, conv)}. Shall I cancel that for you?"). {CONSENT_HINT} '
        "Then call cancel_appointment with caller_confirmed 'true'."
    )


# --- Verification wording -------------------------------------------------------


def idnv_wording(text: str) -> str:
    """idnv's shared returns in this template's words: a patient record, not an account."""
    text = str(text or "").replace(idnv.MISMATCH_LINE, MISMATCH_LINE)
    for old, new in (
        ("on their account", "on their patient record"),
        ("on your account", "on your patient record"),
        (
            "whether there's an account on the number",
            "whether there's a record on the number",
        ),
    ):
        text = text.replace(old, new)
    return text


def gate(conv, resume: str):
    """Strict ID&V gate for a task: None when verified, else the instruction to verify."""
    said = idnv.require(
        conv, resume, strength=idnv.STRICT, caller_id_question=CALLER_ID_QUESTION
    )
    return idnv_wording(said) if said else None
