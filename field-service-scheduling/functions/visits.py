"""Visit rules, spoken dates, availability, readbacks and the call-state block, shared by every
task flow.

The flows stay one prompt and a few tools each because the rules live here:
- which day the caller means (a date in words beats the model's date; a weekday that doesn't
  match it is asked about; no same-day or past visits);
- the open arrival windows around that day, as the dispatch API returns them, for the model to
  choose from (it offers two at most, and never one the caller turned down);
- which upcoming visit the caller means;
- what the agent reads back: everything the first time, then only what changed
  (readback_text), and the same-turn marker that refuses a yes given before the question;
- the CALL STATE block every tool response ends with. On voice a step prompt is rendered once,
  when the step is entered, so state shown in the prompt would freeze; the latest tool response
  is always current.
"""

from _gen import *  # <AUTO GENERATED>
import re
from datetime import date, timedelta

import functions.api_client as api_client
import functions.idnv as idnv
from functions.utils import variant_attr

# Said on an indoor booking when the visit_prep_info attribute is blank.
DEFAULT_HOME_LINE = "Someone 18 or over will need to be home to let them in."
WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]
MONTHS = [
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december",
]  # fmt: skip
EARLIEST_WORDS = re.compile(
    r"earliest|soonest|as soon as|asap|first (available|opening)|any ?time|whenever|"
    r"any day|sooner|earlier",
    re.I,
)


@func_description("[UTIL] Visit rules and readback helpers, not callable directly")
def visits(conv: Conversation):
    return "Visit helpers module."


def today(conv) -> date:
    """The call's local date (start_function stores it as today_iso)."""
    try:
        return date.fromisoformat(conv.state.today_iso)
    except (TypeError, ValueError):
        return date.today()


# --- Speaking dates and times ----------------------------------------------


def _ordinal(n: int) -> str:
    suffix = (
        "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


def say_day(iso: str, now: date) -> str:
    """'today', 'tomorrow', 'Friday the 6th' within two weeks, then 'Monday, November 23rd'.
    Never the year."""
    day = date.fromisoformat(iso)
    if day == now:
        return "today"
    if day == now + timedelta(days=1):
        return "tomorrow"
    if (day - now).days <= 14:
        return f"{day.strftime('%A')} the {_ordinal(day.day)}"
    return f"{day.strftime('%A')}, {day.strftime('%B')} {_ordinal(day.day)}"


def on_day(iso: str, now: date) -> str:
    """The day as it follows a verb: 'tomorrow', 'on Friday the 6th'."""
    said = say_day(iso, now)
    return said if said in ("today", "tomorrow") else f"on {said}"


def full_day(iso: str, now: date) -> str:
    """The earliest-window form: 'tomorrow, Tuesday the 3rd'."""
    day = date.fromisoformat(iso)
    said = say_day(iso, now)
    if said in ("today", "tomorrow"):
        return f"{said}, {day.strftime('%A')} the {_ordinal(day.day)}"
    return said


def short_day(iso: str, now: date) -> str:
    """The done-line form: 'tomorrow', 'Thursday' within the week, else 'Friday the 13th'."""
    day = date.fromisoformat(iso)
    if day == now + timedelta(days=1):
        return "tomorrow"
    if 0 < (day - now).days < 7:
        return day.strftime("%A")
    return say_day(iso, now)


def say_time(hhmm: str) -> str:
    """'9', 'noon', '1', '12:30'. No am or pm: the windows can't be confused."""
    hour, minute = (int(x) for x in hhmm.split(":"))
    if hour == 12 and minute == 0:
        return "noon"
    hour12 = hour % 12 or 12
    return f"{hour12}" if not minute else f"{hour12}:{minute:02d}"


def between(window: dict) -> str:
    return f"between {say_time(window['start'])} and {say_time(window['end'])}"


def part_of_day(window: dict) -> str:
    return "morning" if window["start"] < "12:00" else "afternoon"


def say_window(window: dict, now: date) -> str:
    """'tomorrow, between 9 and noon' / 'on Friday the 6th, between 1 and 4'."""
    return f"{on_day(window['date'], now)}, {between(window)}"


# --- Which day the caller means ---------------------------------------------


def parse_date(value: str) -> date | None:
    text = (value or "").strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _date_in_words(text: str, now: date) -> date | None:
    """'November 5th', '5th of November', 'the 5th': the next such date from today."""
    month = next(
        (i for i, m in enumerate(MONTHS, 1) if re.search(rf"\b{m[:3]}\w*\b", text)),
        None,
    )
    num = re.search(r"\b(\d{1,2})(st|nd|rd|th)\b|\bthe (\d{1,2})\b", text)
    if not num:
        return None
    day_no = int(num.group(1) or num.group(3))
    for months_ahead in range(0, 13):
        y, m = divmod(now.month - 1 + months_ahead, 12)
        if month and m + 1 != month:
            continue
        try:
            candidate = date(now.year + y, m + 1, day_no)
        except ValueError:
            continue
        if candidate >= now:
            return candidate
    return None


def _weekday_said(text: str, now: date) -> date | None:
    """A weekday alone is the next one after today; 'next Wednesday' is next week's."""
    hit = next(
        (i for i, d in enumerate(WEEKDAYS) if re.search(rf"\b{d}\b", text)), None
    )
    if hit is None:
        return None
    if re.search(rf"\bnext (week'?s? )?{WEEKDAYS[hit]}\b", text):
        next_monday = now + timedelta(days=7 - now.weekday())
        return next_monday + timedelta(days=hit)
    return now + timedelta(days=(hit - now.weekday() - 1) % 7 + 1)


def resolve_day(
    conv, preferred_date: str, day_said: str
) -> tuple[str, date | None, str]:
    """What day the caller asked for: (mode, day, problem).

    mode is "earliest", "today", "day" or "none" (nothing said yet); problem is an
    instruction when the weekday and the date in their words disagree. The caller's
    words beat the model's date: a date in words wins, then a weekday (the next one after
    today), then 'tomorrow', then the date the model passed."""
    now = today(conv)
    text = (day_said or "").strip().lower()
    model_day = parse_date(preferred_date)
    in_words = _date_in_words(text, now) if text else None
    weekday = _weekday_said(text, now) if text else None
    if in_words and weekday and in_words.weekday() != weekday.weekday():
        return (
            "none",
            None,
            f"The caller said {day_said!r}, but the {_ordinal(in_words.day)} is a "
            f"{in_words.strftime('%A')}. Ask which they meant, then call again with it.",
        )
    if re.search(
        r"\btoday\b|\bthis (morning|afternoon|evening)\b|\btonight\b", text
    ) or (not text and model_day == now):
        return "today", now, ""
    day = in_words or weekday
    if not day and re.search(r"\btomorrow\b", text):
        day = now + timedelta(days=1)
    if not day and re.search(r"\bnext week\b", text):
        day = now + timedelta(days=7 - now.weekday())
    if not day and (
        EARLIEST_WORDS.search(text)
        or preferred_date.strip().lower() in ("earliest", "any", "asap")
    ):
        return "earliest", None, ""
    day = day or model_day
    if not day:
        return "none", None, ""
    if day < now:
        return "earliest", None, ""
    if day == now:
        return "today", now, ""
    return "day", day, ""


# --- Availability ------------------------------------------------------------


def window_key(window: dict) -> tuple[str, str]:
    return (window["date"], window["start"])


def availability_lines(conv, windows: list[dict], wanted: date | None) -> list[str]:
    """One line per working day in the returned range: its open windows, or fully booked."""
    now = today(conv)
    if not windows:
        return []
    first = min(date.fromisoformat(w["date"]) for w in windows)
    last = max(date.fromisoformat(w["date"]) for w in windows)
    if wanted:
        first, last = min(first, wanted), max(last, wanted)
    lines, day = [], first
    while day <= last:
        if api_client.is_working_day(day):
            iso = day.isoformat()
            open_ = [w for w in windows if w["date"] == iso]
            name = say_day(iso, now)
            if open_:
                parts = "; ".join(f"{part_of_day(w)}, {between(w)}" for w in open_)
                full = {"morning", "afternoon"} - {part_of_day(w) for w in open_}
                note = f" (the {full.pop()} is fully booked)" if full else ""
                lines.append(f"- {name} ({iso}): {parts}{note}")
            else:
                lines.append(f"- {name} ({iso}): fully booked")
        day += timedelta(days=1)
    return lines


def store_windows(conv, key: str, windows: list[dict]) -> None:
    store = dict(conv.state.looked_up) if isinstance(conv.state.looked_up, dict) else {}
    store[key] = [dict(w) for w in windows]
    conv.state.looked_up = store


def looked_up(conv, key: str) -> list[dict]:
    store = conv.state.looked_up if isinstance(conv.state.looked_up, dict) else {}
    return list(store.get(key) or [])


def normalise_start(value: str) -> str:
    """'13:00', '1pm', '1:00 pm', '9' -> 'HH:MM'. A bare hour before 8 is the afternoon."""
    text = (value or "").strip().lower().replace(".", "")
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if not m:
        return text
    hour, minute, half = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if half == "pm" and hour < 12 or (not half and hour < 8):
        hour += 12
    if half == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def chosen_window(conv, key: str, visit_date: str, window_start: str) -> dict | None:
    """The window the caller chose, if it was in the last lookup for `key`."""
    day = parse_date(visit_date)
    start = normalise_start(window_start)
    if not day:
        return None
    return next(
        (
            w
            for w in looked_up(conv, key)
            if w["date"] == day.isoformat() and w["start"] == start
        ),
        None,
    )


def lookup(conv, key: str, preferred_date: str, day_said: str) -> dict:
    """Resolve the day the caller asked for and look up the windows around it.

    Returns {"mode", "day", "windows", "problem"}; the windows are stored for the write tool,
    which only accepts one of them."""
    mode, day, problem = resolve_day(conv, preferred_date, day_said)
    if problem or mode == "none":
        return {"mode": mode, "day": None, "windows": [], "problem": problem}
    windows = api_client.windows_around(
        conv, None if mode in ("earliest", "today") else day
    )
    store_windows(conv, key, windows)
    meta = (
        dict(conv.state.lookup_meta) if isinstance(conv.state.lookup_meta, dict) else {}
    )
    meta[key] = {
        "mode": mode,
        "day": day.isoformat() if day else "",
        "turn": _turn(conv),
    }
    conv.state.lookup_meta = meta
    return {
        "mode": mode,
        "day": day,
        "windows": windows,
        "problem": "",
        "part": part_said(day_said),
    }


def part_said(day_said: str) -> str:
    """The part of the day in the caller's words, used only to word the answer: every window
    is still returned."""
    text = (day_said or "").lower()
    if re.search(r"morning|\bam\b|a\.m", text):
        return "morning"
    if re.search(r"afternoon|\bpm\b|p\.m|after lunch", text):
        return "afternoon"
    return ""


def thanks(conv) -> str:
    """'Thanks, Jane. ' when the caller was verified by name in this same turn, else ''."""
    first = conv.state.verified_first_name
    if (
        first
        and conv.state.verified_turn is not None
        and conv.state.verified_turn == _turn(conv)
    ):
        return f"Thanks, {first}. "
    return ""


def lead_line(conv, key: str, window: dict, task: str = "book") -> str:
    """The availability line that goes in front of the first readback when the write is called
    in the same turn as the lookup: the earliest window, or the window asked for when it's free.
    "" when the caller chose the window from offered alternatives."""
    meta = (
        (conv.state.lookup_meta or {}).get(key)
        if isinstance(conv.state.lookup_meta, dict)
        else None
    )
    if not meta or meta.get("turn") is None or meta["turn"] != _turn(conv):
        return ""
    now = today(conv)
    part = day_part(window["date"], part_of_day(window), now)
    first = (looked_up(conv, key) or [None])[0]
    if meta["mode"] == "earliest" and first and window_key(first) == window_key(window):
        if task == "move":
            return f"The earliest I've got is {part}, {between(window)}."
        return (
            f"The earliest we've got is {full_day(window['date'], now)}, with the technician "
            f"arriving {between(window)}."
        )
    if meta["mode"] == "day" and meta["day"] == window["date"]:
        if task == "move":
            return f"Yes, we can do {part} instead."
        return (
            f"Yes, we can get a technician out {_on(part)}, arriving {between(window)}."
        )
    return ""


def day_part(iso: str, part: str, now: date) -> str:
    """'tomorrow morning', 'Thursday morning', 'Wednesday the 11th, in the afternoon'."""
    day = short_day(iso, now)
    if day == "tomorrow" or " the " not in day:
        return f"{day} {part}"
    return f"{day}, in the {part}"


def _on(phrase: str) -> str:
    return phrase if phrase.startswith(("tomorrow", "today")) else f"on {phrase}"


def availability_text(conv, found: dict, write_tool: str, task: str = "book") -> str:
    """What the lookup found and how to say it, in the design's availability wording. `task`
    is "book" or "move" (a move says "instead" and its readback is the move question)."""
    now = today(conv)
    windows = found["windows"]
    lines = availability_lines(
        conv, windows, found["day"] if found["mode"] == "day" else None
    )
    listing = "OPEN ARRIVAL WINDOWS:\n" + "\n".join(lines)
    first = windows[0]
    readback = f"call {write_tool} with it and caller_confirmed='false', and say the readback it returns"
    pick = f"When they choose a window, {readback}."
    rounds = (
        "If they give a constraint ('after 4', 'not Friday', 'a Saturday'), choose from these "
        "windows; don't look up again. If they turn an offer down without one, offer the next "
        "best fit, never a window they've already turned down. A day outside this list: call "
        "this tool again with it. If no window fits their constraint, say so (\"I'm sorry, our "
        'latest arrival window is 1 to 4.") and offer the closest that might, like a Saturday. '
        "After three rounds turned down, offer to put them through to the team. Offer two "
        "windows at most, never three, in words, never as a list."
    )
    if found["mode"] == "earliest":
        how = (
            f"The earliest is {say_window(first, now)}. Before you say anything, call {write_tool} "
            f"now with {first['date']} {first['start']} and caller_confirmed='false'. It returns "
            "what to say: the earliest window and the question. Say only that."
        )
    elif found["mode"] == "today":
        how = (
            "They asked for today. Say: \"We can't book regular visits for the same day, I'm "
            f"afraid. The earliest I've got is {day_part(first['date'], part_of_day(first), now)}, "
            f'{between(first)}. Would that work for you?" If the problem is urgent (a leak '
            "that's pouring or flooding, no heat, no AC, or they say it can't wait), offer the "
            f"emergency team as well. If they say yes to the window, {readback}."
        )
    elif any(w["date"] == found["day"].isoformat() for w in windows):
        iso = found["day"].isoformat()
        that_day = {part_of_day(w): w for w in windows if w["date"] == iso}
        asked = found.get("part", "")
        if asked and asked not in that_day:
            booked = day_part(iso, asked, now)
            how = (
                f"They asked for {booked}, which is fully booked. Say: \"We're fully booked "
                f"{_on(booked)}, I'm afraid, but I could do …\", the two windows below that best "
                'fit what they said, then "Would either of those work?"'
            )
        elif asked or len(that_day) == 1:
            free = that_day[asked] if asked else next(iter(that_day.values()))
            how = (
                f"The window they asked for is open: {say_window(free, now)}. Offer nothing else. "
                f"Before you say anything, call {write_tool} now with {free['date']} "
                f"{free['start']} and caller_confirmed='false'. It returns what to say: that the "
                "window is free, and the question. Say only that."
            )
        else:
            am, pm = that_day["morning"], that_day["afternoon"]
            how = (
                "They didn't say a part of the day and both are open. Ask: \"We've got "
                f"{day_part(iso, 'morning', now)}, {between(am)}, or the afternoon, {between(pm)}. "
                'Which would suit you better?"'
            )
    else:
        day = short_day(found["day"].isoformat(), now)
        how = (
            f"{day} is fully booked. Say: \"I'm sorry, we're fully booked {_on(day)}. The "
            "closest I've got is …\", then exactly two windows that best fit what they said, "
            f'like "{_two(windows, found["day"], now)}", then "Would either of those work?"'
        )
    return f"{listing}\n{how} {pick} {rounds}"


def _two(windows: list[dict], day: date, now: date) -> str:
    """An example pair for a full day: the nearest window before it and after it (or the two
    nearest after). Only the wording's example; the model chooses."""
    iso = day.isoformat()
    before = [w for w in windows if w["date"] < iso][-1:]
    after = [w for w in windows if w["date"] > iso][: 2 - len(before)]
    pair = (before + after)[:2]
    said = [f"{day_part(w['date'], part_of_day(w), now)}, {between(w)}" for w in pair]
    return ", or ".join(said)


# --- Upcoming visits --------------------------------------------------------


def describe_visit(appt: dict, conv) -> str:
    """'a technician coming tomorrow, between 9 and noon, for the leak under your sink'."""
    text = f"a technician coming {say_window(appt, today(conv))}"
    if appt.get("issue"):
        text += f", for {appt['issue']}"
    return text


def visit_label(appt: dict, conv) -> str:
    """'tomorrow morning', 'Friday afternoon': how two visits are named side by side."""
    return f"{short_day(appt['date'], today(conv))} {part_of_day(appt)}"


def upcoming_visits(conv) -> list[dict]:
    customer = idnv.customer(conv)
    if not customer:
        return []
    return api_client.list_appointments(conv, customer["id"])


def selected_visit(conv) -> dict | None:
    wanted = conv.state.selected_appointment_id
    return next((a for a in upcoming_visits(conv) if a["id"] == wanted), None)


def select_visit_for_task(conv, task: str) -> str:
    """Pick the visit a check / move / cancel is about and say what to do.

    One visit: it is selected. Two: name both and ask which. Three or more: ask about the
    soonest and say how many others there are. None: the caller is offered a new booking."""
    conv.state.selected_appointment_id = ""
    visits_ = upcoming_visits(conv)
    if not visits_:
        conv.write_metric("NO_UPCOMING_VISIT", task)
        return (
            "There are no upcoming visits on this account. Say: \"I can't see any upcoming visits "
            'on your account. Would you like me to book one?" If they do, call '
            "start_make_appointment."
        )
    if len(visits_) == 1:
        conv.state.selected_appointment_id = visits_[0]["id"]
        return f"VISIT: {describe_visit(visits_[0], conv)}."
    if len(visits_) == 2:
        a, b = (visit_label(v, conv) for v in visits_)
        return (
            "The caller has two upcoming visits. If they've already said which (a day, or a part "
            "of the day), call choose_visit with it now, without asking. Otherwise say: "
            f'"I can see two visits: {a} and {b}. Which one is it about?" Then call choose_visit '
            "with its date."
        )
    soonest = visits_[0]
    others = len(visits_) - 1
    return (
        f"The caller has {len(visits_)} upcoming visits. Unless they've already said which, ask "
        f'about the soonest and say how many others there are, like: "Is it about '
        f"{describe_visit(soonest, conv).replace('a technician coming', 'the visit')}? You've "
        f'got {others} others booked as well." Then call choose_visit with the date they mean.'
    )


def choose_visit_by_date(conv, visit_date: str, time_of_day: str) -> dict | None:
    part = (time_of_day or "").strip().lower()
    wanted = parse_date(visit_date)
    matches = [
        a
        for a in upcoming_visits(conv)
        if (not wanted or a["date"] == wanted.isoformat())
        and (part not in ("morning", "afternoon") or part_of_day(a) == part)
    ]
    if len(matches) == 1:
        conv.state.selected_appointment_id = matches[0]["id"]
        return matches[0]
    return None


# --- The someone-home sentence -----------------------------------------------


def home_line(conv) -> str:
    """For an indoor visit: the first sentence of visit_prep_info, without an 'unless' clause
    (the visit is indoors), or the default."""
    info = variant_attr(conv, "visit_prep_info")
    if not info:
        return DEFAULT_HOME_LINE
    first = re.split(r"(?<=[.!?])\s+", info.strip())[0]
    first = re.sub(r",?\s+unless\b[^.!?]*", "", first).rstrip(".!? ") + "."
    return first


# --- Readbacks --------------------------------------------------------------


def readback_text(conv, key: str, fields: list[tuple[str, str]]) -> tuple[dict, str]:
    """What to read back for `key`: every field the first time, then only the fields whose
    value changed since the last readback.

    Returns (fields to say, mode): mode is "full" the first time, "changes" when some fields
    changed, and "none" when the caller has already heard all of it. A full or changed readback
    marks the question as asked this turn."""
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    last = store.get(key)
    current = {label: value for label, value in fields if value}
    conv.state.readbacks = {**store, key: current}
    changed = {
        label: value
        for label, value in current.items()
        if last is None or last.get(label) != value
    }
    if last is None or changed:
        mark_question(conv, key)  # the caller is about to hear it and be asked
    if last is None:
        return current, "full"
    return changed, ("changes" if changed else "none")


def readback_is_current(conv, key: str, fields: list[tuple[str, str]]) -> bool:
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    current = {label: value for label, value in fields if value}
    return store.get(key) == current


def heard(conv, key: str) -> dict:
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    return dict(store.get(key) or {})


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


# --- Same-turn marker -------------------------------------------------------
# The history at tool time holds only earlier turns, so its length grows once the
# caller has replied. It is used only as that marker: code never reads what the
# caller said and never counts turns.

NOT_DONE_YET = "NOT DONE YET"


def _turn(conv):
    try:
        return len(conv.history)
    except Exception:
        return None


def turn_now(conv):
    """The same-turn marker (history length only) for other tools to store."""
    return _turn(conv)


def mark_question(conv, key: str) -> None:
    """Record that the question for `key` was just asked (this turn)."""
    turns = (
        dict(conv.state.readback_turns)
        if isinstance(conv.state.readback_turns, dict)
        else {}
    )
    turns[key] = _turn(conv)
    conv.state.readback_turns = turns


def same_turn_as_question(conv, key: str) -> bool:
    """True while the caller can't have answered the question for `key` yet."""
    turns = (
        conv.state.readback_turns if isinstance(conv.state.readback_turns, dict) else {}
    )
    asked = turns.get(key)
    return asked is not None and _turn(conv) == asked


def ask_again(conv, key: str, question: str) -> dict:
    """The re-ask or same-turn refusal: the full readback question, spoken as written. On RSN-1
    an utterance replaces the model's turn, so it ends the tool loop. Marks the question."""
    mark_question(conv, key)
    conv.log.info(NOT_DONE_YET, readback=key)
    return {"utterance": question}


# --- Call state -------------------------------------------------------------


def call_state(conv, task_lines: list[str], next_line: str) -> str:
    lines = [
        "CALL STATE (this replaces any earlier copy; never read it aloud)",
        f"- {idnv.state_line(conv)}",
    ]
    lines += [f"- {line}" for line in task_lines if line]
    lines.append(f"NEXT: {next_line}")
    return "\n".join(lines)
