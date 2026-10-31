"""Visit rules, readbacks and the call-state block, shared by every task flow.

The flows stay one prompt and a few tools each because the rules live here:
- which arrival windows can be offered (no same-day visits, the caller's
  preferred day and time of day, one offer at a time, a cap on rejections);
- which upcoming visit the caller means;
- what the agent reads back: everything the first time, then only what changed
  (readback_text);
- the CALL STATE block every tool response ends with. On voice a step prompt is
  rendered once, when the step is entered, so state shown in the prompt would
  freeze; the latest tool response is always current.
"""

from _gen import *  # <AUTO GENERATED>
from datetime import date, timedelta

import functions.api_client as api_client
import functions.idnv as idnv
from functions.utils import variant_attr

MAX_REJECTED_OFFERS = 3
TIME_OF_DAY = {
    "morning": ("00:00", "12:00"),
    "afternoon": ("12:00", "23:59"),
    "any": ("00:00", "23:59"),
}
# Used only when the visit_prep_info variant attribute is blank.
DEFAULT_PREP_NOTE = "Someone 18 or over needs to be home to let the technician in."
INDOOR_PREP_HINT = (
    "Give the visit prep as what the caller needs to do; don't mention whether the work is "
    "indoors or outdoors."
)


@func_description("[UTIL] Visit rules and readback helpers, not callable directly")
def visits(conv: Conversation):
    return "Visit helpers module."


def prep_note(conv) -> str:
    """What the caller must do for an indoor visit, from the visit_prep_info attribute."""
    return variant_attr(conv, "visit_prep_info", DEFAULT_PREP_NOTE)


def reminder_note(conv) -> str:
    """How we let the caller know before a visit, from the appointment_window_info attribute,
    as an instruction for the confirmation line ("" when the attribute is blank)."""
    info = variant_attr(conv, "appointment_window_info")
    if not info:
        return ""
    return (
        f" From these visit notes, add only the sentence about how we let them know before the "
        f'technician arrives, if there is one: "{info}"'
    )


# --- Speaking dates and times ----------------------------------------------


def _ordinal(n: int) -> str:
    suffix = (
        "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


def say_date(iso: str, today: date | None = None) -> str:
    day = date.fromisoformat(iso)
    text = f"{day.strftime('%A')}, {day.strftime('%B')} {_ordinal(day.day)}"
    if today and day == today + timedelta(days=1):
        return f"tomorrow, {text}"
    return text


def say_time(hhmm: str) -> str:
    hour, minute = (int(x) for x in hhmm.split(":"))
    if hour == 12 and minute == 0:
        return "noon"
    suffix = "am" if hour < 12 else "pm"
    hour12 = hour % 12 or 12
    return f"{hour12}{suffix}" if not minute else f"{hour12}:{minute:02d}{suffix}"


def say_window(window: dict, today: date | None = None) -> str:
    return f"{say_date(window['date'], today)}, arriving between {say_time(window['start'])} and {say_time(window['end'])}"


def say_slot(window: dict, today: date | None = None) -> str:
    """The short form a write confirmation reads back: the day and the window, nothing else."""
    return f"{say_date(window['date'], today)}, {say_time(window['start'])} to {say_time(window['end'])}"


def today(conv) -> date:
    """The call's local date (start_function stores it as today_iso)."""
    try:
        return date.fromisoformat(conv.state.today_iso)
    except (TypeError, ValueError):
        return date.today()


# --- Choosing windows -------------------------------------------------------


def parse_date(value: str, conv) -> date | None:
    text = (value or "").strip()
    if not text or text.lower() in ("na", "any", "none", "asap"):
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        conv.log.warning("Unparseable preferred date", value=text)
        return None


def find_window(
    conv, preferred_date: str, time_of_day: str, after: dict | None = None
) -> tuple[dict | None, str]:
    """The window to offer next, and a note on any rule that changed the request.

    Rules: no same-day or past visits; start from the caller's preferred day;
    keep to their time of day if they gave one; when `after` is set (the caller
    turned the last offer down) offer the next window after it.
    """
    first_day = today(conv) + timedelta(days=1)
    wanted = parse_date(preferred_date, conv)
    note = ""
    if wanted and wanted <= today(conv):
        note = "We can't do same-day visits; the earliest is tomorrow. Say so briefly."
        wanted = first_day
    start = max(wanted or first_day, first_day)
    lo, hi = TIME_OF_DAY.get((time_of_day or "any").lower(), TIME_OF_DAY["any"])
    windows = api_client.open_windows(conv, start)
    if after:
        windows = [
            w
            for w in windows
            if (w["date"], w["start"]) > (after["date"], after["start"])
        ]
    matching = [w for w in windows if lo <= w["start"] < hi]
    if matching:
        if wanted and matching[0]["date"] != wanted.isoformat() and not after:
            note = (
                note + " " if note else ""
            ) + "Nothing is open that day; say this is the nearest."
        return matching[0], note.strip()
    if windows:
        part = (time_of_day or "").lower()
        note = (
            note + " " if note else ""
        ) + f"No {part} windows are open; offer this instead."
        return windows[0], note.strip()
    return None, note


# --- Upcoming visits --------------------------------------------------------


def describe_visit(appt: dict, conv) -> str:
    what = appt.get("service_type") or "service"
    if appt.get("issue"):
        what += f" visit for {appt['issue']}"
    else:
        what += " visit"
    return f"your {what} on {say_window(appt, today(conv))}"


def upcoming_visits(conv) -> list[dict]:
    customer = idnv.customer(conv)
    if not customer:
        return []
    return api_client.list_appointments(conv, customer["id"])


def selected_visit(conv) -> dict | None:
    wanted = conv.state.selected_appointment_id
    return next((a for a in upcoming_visits(conv) if a["id"] == wanted), None)


def select_visit_for_task(conv, task: str) -> str:
    """Pick the visit a confirm / move / cancel is about and say what to do.

    One visit: it is selected. Several: the caller is asked which. None: no
    dead end; the caller is offered a new booking.
    """
    conv.state.selected_appointment_id = ""
    visits_ = upcoming_visits(conv)
    if not visits_:
        conv.write_metric("NO_UPCOMING_VISIT", task)
        return (
            "There are no upcoming visits on this account. Tell the caller that, and offer to "
            "book a new visit (if they want one, call start_make_appointment)."
        )
    if len(visits_) == 1:
        conv.state.selected_appointment_id = visits_[0]["id"]
        return f"VISIT: {describe_visit(visits_[0], conv)}."
    listing = "; ".join(describe_visit(a, conv) for a in visits_)
    return (
        f"The caller has {len(visits_)} upcoming visits: {listing}. Ask which one they mean, then "
        "call choose_visit with its date."
    )


def choose_visit_by_date(
    conv, visit_date: str, time_of_day: str = "any"
) -> dict | None:
    lo, hi = TIME_OF_DAY.get((time_of_day or "any").lower(), TIME_OF_DAY["any"])
    wanted = parse_date(visit_date, conv)
    matches = [
        a
        for a in upcoming_visits(conv)
        if (not wanted or a["date"] == wanted.isoformat()) and lo <= a["start"] < hi
    ]
    if len(matches) == 1:
        conv.state.selected_appointment_id = matches[0]["id"]
        return matches[0]
    return None


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
    changed = [
        value
        for label, value in current.items()
        if last is None or last.get(label) != value
    ]
    if last is None or changed:
        mark_question(conv, key)  # the caller is about to hear it and be asked
    if last is None:
        return "; ".join(current.values()), "full"
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


CONFIRM_MAX_WORDS = 25  # the readback plus the yes-or-no question, as spoken


def read_back_and_ask(lead: str, readback: str, action: str) -> str:
    """A write's readback and its yes-or-no question, as one short instruction. The readback
    holds only the item and the key value; the question names the action, so an 'okay'
    doesn't fit as an answer. The model words it."""
    return (
        f"{lead}, then ask whether to {action}, yes or no, all in one short reply of no more "
        f"than {CONFIRM_MAX_WORDS} words: {readback}. Don't add other details. Wait for the answer."
    )


def spoken_confirmation(readback: str, action: str) -> str:
    """The plainest spoken form of read_back_and_ask, used to check the word budget."""
    return f"{readback}. Shall I {action}, yes or no?"


def yes_no_question(what: str, lead: str = "Then ask") -> str:
    """The question a write's readback ends with. It names the action and the item, so an
    'okay' doesn't fit as an answer; the model words it."""
    return (
        f"{lead} a yes-or-no question that names it: whether to {what}, yes or no. "
        "Wait for the answer."
    )


# --- Same-turn marker -------------------------------------------------------
# The history at tool time holds only earlier turns, so its length grows once the
# caller has replied. It is used only as that marker: code never reads what the
# caller said and never counts turns.

NOT_DONE_YET = "NOT DONE YET: wait for the caller's answer to the yes-or-no question, then call again."


def _turn(conv):
    try:
        return len(conv.history)
    except Exception:
        return None


def mark_question(conv, key: str) -> None:
    """Record that the yes-or-no question for `key` was just asked (this turn)."""
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


# --- Call state -------------------------------------------------------------


def call_state(conv, task_lines: list[str], next_line: str) -> str:
    lines = [
        "CALL STATE (this replaces any earlier copy; never read it aloud)",
        f"- {idnv.state_line(conv)}",
    ]
    lines += [f"- {line}" for line in task_lines if line]
    lines.append(f"NEXT: {next_line}")
    return "\n".join(lines)
