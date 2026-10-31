from _gen import *  # <AUTO GENERATED>
from functions import idnv, visits
from functions.handoff import handoff

READBACK_KEY = "move"


def move_request(conv) -> dict:
    req = conv.state.move_request
    if (
        not isinstance(req, dict)
        or req.get("appointment_id") != conv.state.selected_appointment_id
    ):
        req = {
            "appointment_id": conv.state.selected_appointment_id or "",
            "preferred_date": "",
            "time_of_day": "any",
            "offer": None,
            "rejected": 0,
        }
    return dict(req)


def move_fields(conv, req: dict) -> list[tuple[str, str]]:
    offer = req.get("offer") or {}
    visit = visits.selected_visit(conv)
    return [
        ("visit", f"your visit on {visits.say_date(visit['date'])}" if visit else ""),
        ("when", f"to {visits.say_slot(offer, visits.today(conv))}" if offer else ""),
    ]


def move_question(conv, req: dict) -> str:
    offer = req.get("offer") or {}
    day = (
        visits.say_date(offer["date"], visits.today(conv)) if offer else "the new time"
    )
    return f"move the visit to {day}"


def move_state(conv) -> str:
    req = move_request(conv)
    visit = visits.selected_visit(conv)
    offer = req.get("offer")
    lines = [
        "Task: move an existing visit",
        "Visit: " + (visits.describe_visit(visit, conv) if visit else "not chosen yet"),
        "Wants it: "
        + (req["preferred_date"] or "not said yet")
        + ("" if req["time_of_day"] == "any" else f", {req['time_of_day']}"),
        "Offered: "
        + (visits.say_window(offer, visits.today(conv)) if offer else "nothing yet"),
    ]
    if not visit:
        nxt = "Find out which visit they mean."
    elif not req["preferred_date"]:
        nxt = "Ask when would suit them instead."
    elif offer:
        nxt = (
            "Wait for the caller's yes or no to moving the visit to the offered window."
        )
    else:
        nxt = "Call find_new_time."
    return visits.call_state(conv, lines, nxt)


@func_description(
    "Find a new arrival window for the visit being moved, from the caller's preferred day and time of day, or the next one after the window they turned down."
)
@func_parameter(
    "preferred_date",
    "A specific day they asked for, as YYYY-MM-DD (the first day of a range such as 'next week'), or 'any' if they're flexible about the day. Empty string if they only turned the last offer down.",
)
@func_parameter("time_of_day", "'morning', 'afternoon' or 'any'.")
@func_parameter(
    "wants_different_time",
    "'true' only when the caller turned down the window you offered without saying what they want instead. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me see what we have.", 3), ("One more moment.", 3)],
)
def find_new_time(
    conv: Conversation,
    flow: Flow,
    preferred_date: str,
    time_of_day: str,
    wants_different_time: str,
):
    if not idnv.is_verified(conv):
        return idnv.require(conv, "reschedule_appointment")
    if not visits.selected_visit(conv):
        return f"First find out which visit they want to move.\n\n{move_state(conv)}"

    req = move_request(conv)
    before = (req["preferred_date"], req["time_of_day"])
    if preferred_date.strip():
        req["preferred_date"] = preferred_date.strip()
    if time_of_day.strip().lower() in visits.TIME_OF_DAY:
        req["time_of_day"] = time_of_day.strip().lower()
    rejected = str(wants_different_time).strip().lower() == "true"

    after = None
    if rejected and req["offer"]:
        req["rejected"] += 1
        conv.write_metric("OFFERED_SLOT_REJECTED")
        if req["rejected"] >= visits.MAX_REJECTED_OFFERS:
            conv.state.move_request = req
            return handoff(
                conv,
                "RESCHEDULE_OFFERED_SLOTS_REJECTED",
                "I'm sorry I couldn't find a time that suits. Let me put you through to our "
                "scheduling team, one moment please.",
                "CUSTOMER_CARE",
            )
        after = req["offer"]
    if not req["preferred_date"]:
        req["preferred_date"] = "any" if rejected else ""
    if not req["preferred_date"]:
        conv.state.move_request = req
        return f"Ask when would suit them instead.\n\n{move_state(conv)}"

    note = ""
    if (
        rejected
        or before != (req["preferred_date"], req["time_of_day"])
        or not req["offer"]
    ):
        window, note = visits.find_window(
            conv, req["preferred_date"], req["time_of_day"], after
        )
        if window is None:
            conv.state.move_request = req
            return handoff(
                conv,
                "NO_AVAILABILITY_FOUND",
                "I'm sorry, I can't see any open times in the next two weeks. Let me put you "
                "through to our scheduling team, one moment please.",
                "CUSTOMER_CARE",
            )
        req["offer"] = window
    conv.state.move_request = req
    conv.write_metric("SLOT_OFFERED")

    text, mode = visits.readback_text(conv, READBACK_KEY, move_fields(conv, req))
    if mode == "none":
        return (
            "Nothing has changed since the readback. If the caller's latest reply was a clear yes "
            "to moving it, call reschedule_appointment with caller_confirmed='true'; otherwise "
            f"{visits.yes_no_question(move_question(conv, req), 'ask')}\n\n{move_state(conv)}"
        )
    lead = "Offer to move it" if mode == "full" else "Tell the caller only what changed"
    say = visits.read_back_and_ask(lead, text, "move it")
    return f"{note + ' ' if note else ''}{say}\n\n{move_state(conv)}"
