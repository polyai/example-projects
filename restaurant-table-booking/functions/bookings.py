"""Booking rules, readbacks and the call-state block, shared by every task flow.

The flows stay one prompt and a few tools each because the rules live here:
- the day the caller means: a date in words beats the model's date, a weekday
  alone is the next one after today, and a weekday that doesn't match the date
  is asked about (resolve_day);
- whether a table can be offered: opening hours and last seating, 15 minutes'
  notice for today, no past dates, closed days, room for the whole party. When
  the time asked for is taken, every free time the booking API returns in its
  window (check_table); the model picks which to offer. When a day is full, the
  nearest day before and after with a table. The next free table from now;
- the largest party the agent can book (settings.max_party_size);
- which upcoming booking the caller means;
- what the caller has heard before a write (readback_changes), and the turn the
  readback question was asked, so a yes in that same turn writes nothing;
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
BOOKING_NOTICE_MINUTES = 15  # a table today must start at least this far ahead
ASK = (
    ' Then ask: "Would either of those work for you?" (one time: "Would that work for you?"). '
    "Nothing is held yet, so never ask whether to book."
)
SEARCH_DAYS = 7  # how far the next-free-table and nearest-day searches look

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}  # fmt: skip
_SAY_NUMBER = {v: k for k, v in _NUMBER_WORDS.items()}
_WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]
_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
           "september", "october", "november", "december"]  # fmt: skip


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


def is_true(value) -> bool:
    return str(value or "").strip().lower() == "true"


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


def is_any_time(value) -> bool:
    return bool(
        re.fullmatch(r"\s*(any|any ?time|whenever|anytime)\s*", str(value or ""), re.I)
    )


def parse_time(value) -> str:
    """'19:00', '7pm', '7:30 pm', 'around 7:30', 'noon' -> 'HH:MM'; '' if not a time."""
    text = str(value or "").strip().lower().replace(".", "")
    text = re.sub(r"^(around|about|at|roughly|maybe)\s+", "", text)
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


def _date_in_words(conv, said: str) -> date | None:
    """'October 22nd', 'the 22nd of October', 'the 6th' -> the next such date."""
    base = today(conv)
    month = next(
        (
            i + 1
            for i, m in enumerate(_MONTHS)
            if re.search(rf"\b{m[:3]}[a-z]*\b", said)
        ),
        0,
    )
    day_match = re.search(r"\b(\d{1,2})(st|nd|rd|th)?\b", said)
    if not day_match or (not month and not day_match.group(2)):
        return None
    day = int(day_match.group(1))
    for ahead in range(0, 13):
        y, m = divmod(base.month - 1 + ahead, 12)
        y, m = base.year + y, m + 1
        if month and m != month:
            continue
        try:
            found = date(y, m, day)
        except ValueError:
            continue
        if found >= base:
            return found
    return None


def resolve_day(conv, value, day_said) -> tuple[date | None, str]:
    """The day the caller means, and a question to ask instead when it's unclear.

    A date in words beats the model's date; a weekday that doesn't match that date
    is asked about, never guessed. A weekday alone is the next one after today
    (or the one a week later, for "next Friday", when the model passed that).
    """
    said = str(day_said or "").strip().lower()
    given = parse_date(conv, value)
    base = today(conv)
    if re.search(r"\b(today|tonight|this evening|lunchtime today)\b", said):
        return base, ""
    if re.search(r"\bday after tomorrow\b", said):
        return base + timedelta(days=2), ""
    if re.search(r"\btomorrow\b", said):
        return base + timedelta(days=1), ""
    weekday = next(
        (i for i, d in enumerate(_WEEKDAYS) if re.search(rf"\b{d}", said)), None
    )
    in_words = _date_in_words(conv, said)
    if in_words:
        if weekday is not None and in_words.weekday() != weekday:
            return None, (
                f"Ask which day they meant: the {_ordinal(in_words.day)} is a "
                f"{in_words.strftime('%A')}, not a {_WEEKDAYS[weekday].capitalize()}."
            )
        return in_words, ""
    if (
        weekday is None
        and not in_words
        and re.search(r"\b(next|this|that|the following) week\b|\bweek\b", said)
    ):
        return (
            None,
            'Ask which day they\'d like: "Of course. What day would work for you?"',
        )
    if weekday is not None:
        nxt = base + timedelta(days=(weekday - base.weekday() - 1) % 7 + 1)
        if re.search(r"\bnext\b", said) and given == nxt + timedelta(days=7):
            return given, ""
        return nxt, ""
    return given, ""


# --- Saying things ----------------------------------------------------------


def _ordinal(n: int) -> str:
    suffix = (
        "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


def say_time(hhmm: str) -> str:
    """'19:00' -> '7', '19:30' -> '7:30', '12:00' -> 'noon', '11:30' -> '11:30am'."""
    h, m = (int(x) for x in hhmm.split(":"))
    if (h, m) == (12, 0):
        return "noon"
    h12 = h % 12 or 12
    text = f"{h12}" if not m else f"{h12}:{m:02d}"
    return f"{text}am" if h < 12 else text


def say_party(n) -> str:
    """'two', 'four', '12'."""
    return _SAY_NUMBER.get(int(n), str(n))


def say_people(n) -> str:
    return f"{say_party(n)} {'person' if int(n) == 1 else 'people'}"


def day_name(conv, day_iso: str) -> str:
    """'today', 'tomorrow', 'Friday the 6th' within two weeks, else 'Saturday, December 12th'."""
    day = date.fromisoformat(day_iso)
    ahead = (day - today(conv)).days
    if ahead == 0:
        return "today"
    if ahead == 1:
        return "tomorrow"
    if 0 < ahead < 14:
        return f"{day.strftime('%A')} the {_ordinal(day.day)}"
    return f"{day.strftime('%A')}, {day.strftime('%B')} {_ordinal(day.day)}"


def when(conv, day_iso: str, hhmm: str) -> str:
    """The day and time in a readback: 'tonight at 7:30', 'tomorrow at 7',
    'on Friday the 6th at 8'."""
    day = day_name(conv, day_iso)
    if day == "today":
        return f"{'tonight' if hhmm >= '17:00' else 'today'} at {say_time(hhmm)}"
    if day == "tomorrow":
        return f"tomorrow at {say_time(hhmm)}"
    return f"on {day} at {say_time(hhmm)}"


def short_when(conv, day_iso: str, hhmm: str) -> str:
    """The day and time in a done line: '7:30 tonight', 'tomorrow at 7', 'Friday at 8'."""
    day = date.fromisoformat(day_iso)
    ahead = (day - today(conv)).days
    if ahead == 0:
        return f"{say_time(hhmm)} {'tonight' if hhmm >= '17:00' else 'today'}"
    if ahead == 1:
        return f"tomorrow at {say_time(hhmm)}"
    if 0 < ahead < 7:
        return f"{day.strftime('%A')} at {say_time(hhmm)}"
    return f"{day_name(conv, day_iso)} at {say_time(hhmm)}"


def goodbye_day(conv, day_iso: str, hhmm: str = "") -> str:
    """'tonight' ('later today' for a table before 5pm), 'tomorrow', 'on Friday',
    'on Saturday the 14th'."""
    day = date.fromisoformat(day_iso)
    ahead = (day - today(conv)).days
    if ahead == 0:
        return "later today" if hhmm and hhmm < "17:00" else "tonight"
    if ahead == 1:
        return "tomorrow"
    if 0 < ahead < 7:
        return f"on {day.strftime('%A')}"
    return f"on {day_name(conv, day_iso)}"


def table_for(conv, party_size, day_iso: str, hhmm: str) -> str:
    """'a table for four tomorrow at 7'."""
    return f"a table for {say_party(party_size)} {when(conv, day_iso, hhmm)}"


def describe_booking(conv, booking: dict, with_name: bool = False) -> str:
    text = table_for(conv, booking["party_size"], booking["date"], booking["time"])
    if with_name:
        text += f", under {booking['first_name']} {booking['last_name']}".rstrip()
    if booking.get("notes"):
        text += f", with a note: {booking['notes']}"
    return text


def spell_phone(digits: str) -> str:
    return idnv.spell_phone(digits)


# --- Availability -----------------------------------------------------------


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _bookable(conv, day: date, times: list[str]) -> list[str]:
    """The times a table can start: within hours and last seating, with notice today."""
    earliest = None
    if day == today(conv):
        soonest = now(conv) + timedelta(minutes=BOOKING_NOTICE_MINUTES)
        earliest = soonest.hour * 60 + soonest.minute
    return [
        t
        for t in times
        if hours.can_seat(conv, day, t)
        and (earliest is None or _minutes(t) >= earliest)
    ]


def free_times(conv, day: date, hhmm: str, party: int, ignore: str = "") -> list[str]:
    """The API's free times in its window around hhmm (the whole day with no time),
    that can be booked."""
    return _bookable(
        conv, day, api_client.search_availability(conv, day, hhmm, party, ignore)
    )


def _says_times(times: list[str]) -> str:
    return ", ".join(say_time(t) for t in times)


def _pm(day: date, hhmm: str, conv) -> str:
    """No am or pm: 'seven' means 7pm when 7am can't be seated."""
    if hhmm and _minutes(hhmm) < 12 * 60 and not hours.can_seat(conv, day, hhmm):
        later = f"{_minutes(hhmm) // 60 + 12:02d}:{hhmm[3:]}"
        if hours.can_seat(conv, day, later):
            return later
    return hhmm


def nearest_days(
    conv, day: date, hhmm: str, party: int, ignore: str = ""
) -> list[tuple]:
    """The nearest day before (not before today) and after `day`, within SEARCH_DAYS
    each way, with a free table: [(date, [times]), ...]."""
    found = []
    for step in (-1, 1):
        for n in range(1, SEARCH_DAYS + 1):
            other = day + timedelta(days=step * n)
            if other < today(conv):
                break
            times = free_times(conv, other, hhmm, party, ignore)
            if times:
                found.append((other, times))
                break
    return found


def next_free(conv, party: int) -> tuple[date, str] | None:
    """The first free table for the party from now, up to SEARCH_DAYS ahead."""
    for n in range(SEARCH_DAYS + 1):
        day = today(conv) + timedelta(days=n)
        times = free_times(conv, day, "", party)
        if times:
            return day, times[0]
    return None


def check_table(conv, day: date, wanted: str, party: int, ignore: str = "") -> dict:
    """Can `party` have a table on `day` at `wanted` ('' for any time)?

    Returns {"outcome": ..., "time": HH:MM, "say": what the model should do}:
      free     the time asked for is free (time is the one to hold)
      full     it isn't; say lists every free time in the API's window
      day_full nothing that day; say lists the nearest days before and after
      closed   closed that day (hours known)
      outside  outside hours, after last seating, too soon, or in the past
    """
    when_said = (
        f"{say_time(wanted)} on {day.strftime('%A')}" if wanted else day.strftime("%A")
    )
    if day < today(conv):
        return {
            "outcome": "outside",
            "say": "That date has already passed. Ask which day they meant.",
        }
    shifts = hours.shifts_on(conv, day)
    if shifts == []:
        return {
            "outcome": "closed",
            "say": (
                f"Say: \"We're closed on {day.strftime('%A')}s, I'm afraid. Would another day "
                'work for you?"'
            ),
        }
    wanted = _pm(day, wanted, conv)
    if wanted and wanted not in _bookable(conv, day, [wanted]):
        whole_day = free_times(conv, day, "", party, ignore)
        near = sorted(whole_day, key=lambda t: abs(_minutes(t) - _minutes(wanted)))[:2]
        if shifts is None:
            why = "that time can't be booked. Never give opening hours or say we're closed"
        elif day == today(conv) and hours.can_seat(conv, day, wanted):
            why = "it's too soon to book that time today"
        else:
            why = f"we're open {hours.say_shifts(shifts)} that day, with the last table half an hour before closing"
        if not near:
            return {
                "outcome": "day_full",
                "say": f"{say_time(wanted)} can't be booked ({why}), and nothing else is free that day."
                + _nearest_line(conv, day, wanted, party, ignore),
            }
        return {
            "outcome": "full",
            "times": near,
            "say": (
                f"{say_time(wanted)} can't be booked: {why}. Say so briefly and offer the nearest "
                f"free times: {_says_times(near)}." + ASK
            ),
        }
    times = free_times(conv, day, wanted, party, ignore)
    if wanted and wanted in times:
        return {"outcome": "free", "time": wanted, "times": times}
    if not times:
        return {
            "outcome": "day_full",
            "say": (
                f"Nothing is free for {say_party(party)} on {day.strftime('%A')}. Say: \"I'm sorry, "
                f"we're fully booked for {say_party(party)} on {day.strftime('%A')}.\""
            )
            + _nearest_line(conv, day, wanted, party, ignore),
        }
    if not wanted:
        return {
            "outcome": "full",
            "times": times,
            "say": (
                f"Free times for {say_party(party)} on {day.strftime('%A')}: {_says_times(times)}. "
                "Offer two at most that fit what the caller said." + ASK
            ),
        }
    return {
        "outcome": "full",
        "times": times,
        "say": (
            f"{when_said} is fully booked. The free times around it are: {_says_times(times)}. "
            f"Say: \"We're fully booked at {when_said}, I'm afraid, but I could do ...\" with the "
            "two (at most) that best fit what the caller said, never a time they turned down. "
            'Never say a time is taken or gone. A constraint these times answer ("after 8", '
            '"earlier"): choose from this list, and if none fits, say we\'re fully booked then too.'
            + ASK
        ),
    }


def _nearest_line(conv, day: date, wanted: str, party: int, ignore: str) -> str:
    near = nearest_days(conv, day, wanted, party, ignore)
    if not near:
        return (
            " Nothing is free within a week either way. Ask if another day might work."
        )
    options = "; ".join(
        f"{d.strftime('%A')} ({day_name(conv, d.isoformat())}): {_says_times(t)}"
        for d, t in near
    )
    return (
        f" The nearest days with a table: {options}. Offer one time on each day, the closest to "
        "what they asked for (\"The closest I've got is Friday at 8:30 or Sunday at 6. Would either "
        'of those work?"). If it really has to be that day'
        + (
            f", say: \"We do keep a bit of space for walk-ins, but I can't promise anything on a "
            f'{day.strftime("%A")}." and ask if another day might work.'
            if _attr(conv, "walk_in_info")
            else ", ask if another day might work."
        )
    )


def _attr(conv, name: str) -> str:
    return str(getattr(conv.variant, name, "") or "").strip() if conv.variant else ""


# --- Readbacks --------------------------------------------------------------


def _turn(conv):
    """The history's length, used only as a same-turn marker: at tool time the
    history holds earlier turns, so it grows once the caller has replied. None if
    the platform doesn't expose it."""
    try:
        return len(conv.history)
    except Exception:
        return None


def readback_changes(conv, key: str, fields: list[tuple[str, str]]) -> tuple[dict, str]:
    """What the caller hasn't heard of `fields`, as {label: value}, and the mode:
    "full" the first time, "changes" when some changed, "none" when nothing did.

    Two calls in one turn (a new number and a new time said together) compare with
    what the caller had heard before that turn, so the second return names both."""
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    entry = store.get(key)
    turn = _turn(conv)
    current = {label: value for label, value in fields if value}
    if entry is None:
        conv.state.readbacks = {
            **store,
            key: {"heard": current, "base": None, "turn": turn},
        }
        return current, "full"
    base = (
        entry["base"]
        if turn is not None and entry.get("turn") == turn
        else entry["heard"]
    )
    conv.state.readbacks = {
        **store,
        key: {"heard": current, "base": base, "turn": turn},
    }
    if base is None:
        return current, "full"
    changed = {
        label: value for label, value in current.items() if base.get(label) != value
    }
    return changed, ("changes" if changed else "none")


def readback_is_current(conv, key: str, fields: list[tuple[str, str]]) -> bool:
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    current = {label: value for label, value in fields if value}
    return (store.get(key) or {}).get("heard") == current


def remember_readback(conv, key: str, fields: list[tuple[str, str]]) -> None:
    """Record that the caller has heard these values (e.g. an existing booking read out)."""
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    current = {label: value for label, value in fields if value}
    conv.state.readbacks = {
        **store,
        key: {"heard": current, "base": current, "turn": None},
    }


def forget_readback(conv, key: str) -> None:
    store = dict(conv.state.readbacks) if isinstance(conv.state.readbacks, dict) else {}
    store.pop(key, None)
    conv.state.readbacks = store


def mark_asked(conv, key: str) -> None:
    """Record the turn in which the readback question for `key` was asked."""
    store = conv.state.asked_turns if isinstance(conv.state.asked_turns, dict) else {}
    conv.state.asked_turns = {**store, key: _turn(conv)}


def asked_this_turn(conv, key: str) -> bool:
    """True while the caller hasn't replied since the question for `key` was asked,
    so a 'true' in the same turn can't be their answer."""
    store = conv.state.asked_turns if isinstance(conv.state.asked_turns, dict) else {}
    turn = _turn(conv)
    return turn is not None and key in store and store[key] == turn


def not_done_yet(sentence: str) -> dict:
    """A 'true' in the same turn as the readback question can't be the caller's answer.
    Speak the readback and its question (an utterance ends the tool loop: on RSN-1 a
    text refusal here let the model call the write again and again until the turn
    failed) and write nothing."""
    return {"utterance": sentence}


# --- Lines the caller must hear ---------------------------------------------


def said_line(conv, line: str) -> None:
    """Record a done line a tool speaks, and the turn, so end_call in that same turn
    says it before the goodbye (the goodbye would otherwise replace it)."""
    conv.state.must_hear = {"line": line, "turn": _turn(conv)}


def unheard_line(conv) -> str:
    entry = conv.state.must_hear if isinstance(conv.state.must_hear, dict) else {}
    turn = _turn(conv)
    if entry.get("line") and turn is not None and entry.get("turn") == turn:
        return entry["line"]
    return ""


# --- Existing bookings ------------------------------------------------------


def upcoming(conv) -> list[dict]:
    guest = idnv.customer(conv)
    if not guest:
        return []
    return api_client.list_bookings(conv, guest["id"])


def selected(conv) -> dict | None:
    wanted = conv.state.selected_booking_id
    return next((b for b in upcoming(conv) if b["id"] == wanted), None)


def _brief(conv, booking: dict) -> str:
    """'Wednesday at 6'."""
    return short_when(conv, booking["date"], booking["time"])


def select_for_task(conv, task: str) -> str:
    """Pick the booking a check / change / cancel is about and say what to do.

    One booking: it is selected. Two: both are named and the caller is asked which.
    Three or more: the soonest is asked about first, saying how many others there
    are. None: no dead end; the caller is offered a new booking or the team.
    """
    conv.state.selected_booking_id = ""
    conv.state.booking_choice_unclear = 0
    mine = upcoming(conv)
    if not mine:
        conv.write_metric("NO_UPCOMING_BOOKING", task)
        return (
            "There are no upcoming bookings under this name and number. Tell the caller that, "
            "and ask if they'd like to make a new booking (if yes, call start_make_booking). If "
            "they're sure they have one, offer to put them through to the team (handoff with "
            "handoff_reason=NO_BOOKING_FOUND)."
        )
    if len(mine) == 1:
        conv.state.selected_booking_id = mine[0]["id"]
        return ""
    if len(mine) == 2:
        return (
            f'Say: "I can see two bookings: {_brief(conv, mine[0])} and {_brief(conv, mine[1])}. '
            'Which one is it about?" Then call choose_booking with their answer.'
        )
    return (
        f"The caller has {len(mine)} upcoming bookings. Ask about the soonest first, and say how "
        f'many others there are: "I can see {len(mine)} bookings. The soonest is '
        f'{describe_booking(conv, mine[0])}. Is it that one, or one of the other {len(mine) - 1}?" '
        "Then call choose_booking with their answer."
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


def require(conv, flow_name: str):
    """The ID&V gate for finding a booking, in this design's words."""
    gate = idnv.require(conv, flow_name, caller_id_question=CALLER_ID_QUESTION)
    return booking_words(gate) if isinstance(gate, str) else gate


CALLER_ID_QUESTION = "Is the booking under the number you're calling from?"
NUMBER_ASK = "What's the phone number the booking's under?"
NAME_ASK = "And what name's the booking under?"


def booking_words(text: str) -> str:
    """idnv speaks of accounts; a restaurant has bookings."""
    return (
        text.replace(
            "ask for the phone number on their account.", f'ask: "{NUMBER_ASK}"'
        )
        .replace(
            "Ask for the phone number on their account, starting with the area code.",
            f'Ask: "{NUMBER_ASK}"',
        )
        .replace("Ask for the full name on the account.", f'Ask: "{NAME_ASK}"')
        .replace("ask for the phone number on their account", f'ask "{NUMBER_ASK}"')
        .replace(
            "the full name the account is under",
            "whether the booking might be under someone else's name",
        )
        .replace(
            "doesn't match the account on that number",
            "doesn't match the booking on that number",
        )
        .replace(
            "whether you found an account or whose it is",
            "whether you found a booking or whose it is",
        )
    )


# --- Call state -------------------------------------------------------------


def call_state(conv, task_lines: list[str], next_line: str) -> str:
    lines = [
        "CALL STATE (this replaces any earlier copy; never read it aloud)",
        f"- {idnv.state_line(conv)}",
    ]
    lines += [f"- {line}" for line in task_lines if line]
    lines.append(f"NEXT: {next_line}")
    return "\n".join(lines)
