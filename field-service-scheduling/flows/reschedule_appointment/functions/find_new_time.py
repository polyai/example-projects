from _gen import *  # <AUTO GENERATED>
from functions import idnv, visits
from functions.handoff import handoff

READBACK_KEY = "move"
LOOKUP_KEY = "move"
ASK_WHEN = "What day would work better for you?"
NO_AVAILABILITY = (
    "I'm sorry, I can't see any openings in the next two weeks. Let me put you through to our "
    "scheduling team, who may be able to fit you in. One moment, please."
)


def move_fields(conv, window: dict | None) -> list[tuple[str, str]]:
    """What the caller says yes to: only what changes, the new day and window."""
    now = visits.today(conv)
    return [
        ("day", visits.say_day(window["date"], now) if window else ""),
        ("window", visits.between(window) if window else ""),
    ]


def move_question(conv, window: dict) -> str:
    day = visits.say_day(window["date"], visits.today(conv))
    return f"Shall I move your visit to {day}, arriving {visits.between(window)}?"


def move_state(conv) -> str:
    visit = visits.selected_visit(conv)
    windows = visits.looked_up(conv, LOOKUP_KEY)
    lines = [
        "Task: move an existing visit",
        "Visit: " + (visits.describe_visit(visit, conv) if visit else "not chosen yet"),
        f"Windows looked up: {len(windows)}"
        if windows
        else "Windows looked up: none yet",
    ]
    if not visit:
        nxt = "Find out which visit they mean, then call choose_visit."
    elif not windows:
        nxt = f'Ask "{ASK_WHEN}" unless they\'ve said, then call find_new_time.'
    else:
        nxt = "Offer windows from the latest find_new_time response; call reschedule_appointment with the one they choose."
    return visits.call_state(conv, lines, nxt)


@func_description(
    "Look up open arrival windows for the visit being moved: the day the caller asked for and the days around it, or the earliest from tomorrow. Call it whenever they say or change when they'd like it instead, or ask for a day outside the windows you already have."
)
@func_parameter(
    "preferred_date",
    "The day they asked for as YYYY-MM-DD, from the date guide; 'earliest' if they want it as soon as possible or earlier. Empty if they haven't said.",
)
@func_parameter(
    "day_said",
    "Their words for the day, with the part of the day if they said one, e.g. 'Saturday morning', 'same time on Friday', 'as soon as possible'. Empty if they haven't said.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me just check what we've got.", 3), ("Nearly there.", 3)],
)
def find_new_time(conv: Conversation, flow: Flow, preferred_date: str, day_said: str):
    if not idnv.is_verified(conv):
        return idnv.require(conv, "reschedule_appointment")
    if not visits.selected_visit(conv):
        return f"First find out which visit they want to move.\n\n{move_state(conv)}"

    said = str(day_said or "")
    if "same time" in said.lower() and not visits.part_said(said):
        said += f" {visits.part_of_day(visits.selected_visit(conv))}"  # the visit's own part of day
    avail = visits.lookup(conv, LOOKUP_KEY, str(preferred_date or ""), said)
    if avail["problem"]:
        return f"{avail['problem']}\n\n{move_state(conv)}"
    if avail["mode"] == "none":
        return f'Ask: "{ASK_WHEN}" Then call this again.\n\n{move_state(conv)}'
    if not avail["windows"]:
        conv.write_metric("NO_AVAILABILITY_FOUND")
        return handoff(conv, "NO_AVAILABILITY_FOUND", NO_AVAILABILITY, "CUSTOMER_CARE")
    conv.write_metric("SLOT_OFFERED")
    text = visits.availability_text(conv, avail, "reschedule_appointment", task="move")
    return f"{text}\n\n{move_state(conv)}"
