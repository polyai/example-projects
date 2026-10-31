from _gen import *  # <AUTO GENERATED>
import functions.appointments as appointments
import functions.idnv as idnv
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
    appt = appointments.selected(conv)
    return [
        ("appointment", f"moving {appointments.describe(appt, conv)}" if appt else ""),
        (
            "when",
            f"to {appointments.say_slot(offer, appointments.today(conv))}"
            if offer
            else "",
        ),
    ]


def move_words(conv, req: dict) -> str:
    """The move confirmation the caller hears: the appointment's type and the new
    slot. The old day and time only when they have more than one appointment, and
    the doctor only when it changes."""
    appt = appointments.selected(conv) or {}
    today = appointments.today(conv)
    kind = str(appt.get("type") or "appointment").lower()
    offer = req["offer"]
    item = f"your {kind}"
    if appt.get("date") and len(appointments.upcoming(conv)) > 1:
        item += f" on {appointments.say_slot(appt, today, provider=False)}"
    changes_doctor = offer.get("provider") != appt.get("provider")
    when = appointments.say_slot(offer, today, provider=changes_doctor)
    return f"Shall I move {item} to {when}, yes or no?"


def move_question(conv, req: dict, lead: str = "Ask") -> str:
    return appointments.ask_yes_no(move_words(conv, req), lead)


def move_state(conv) -> str:
    req = move_request(conv)
    appt = appointments.selected(conv)
    offer = req.get("offer")
    today = appointments.today(conv)
    lines = [
        "Task: move an existing appointment",
        "Appointment: "
        + (appointments.describe(appt, conv) if appt else "not chosen yet"),
        "Wants it: "
        + (req["preferred_date"] or "not said yet")
        + ("" if req["time_of_day"] == "any" else f", {req['time_of_day']}"),
        "Offered: " + (appointments.say_slot(offer, today) if offer else "nothing yet"),
    ]
    if not appt:
        nxt = "Find out which appointment they mean."
    elif not req["preferred_date"]:
        nxt = (
            "Ask when would suit them instead. If they're flexible, call find_new_time with "
            "preferred_date='any'."
        )
    elif offer:
        nxt = (
            "Wait for the caller's answer to the yes-or-no question about moving it to this slot. "
            "A clear yes means move it: call reschedule_appointment with caller_confirmed='true'. "
            "'Okay', 'mm-hm' or anything unclear is not a yes: ask the yes-or-no question again."
        )
    else:
        nxt = "Call find_new_time."
    return appointments.call_state(conv, lines, nxt)


@func_description(
    "Find a new slot for the appointment being moved, from the caller's preferred day and time of day, or the next one after the slot they turned down."
)
@func_parameter(
    "preferred_date",
    "The day they asked for, as YYYY-MM-DD from the date guide; for a range, its first day ('next week' is the Monday the guide names). 'any' only if they don't mind which day or want the earliest. Empty string if they only turned the last offer down.",
)
@func_parameter("time_of_day", "'morning', 'afternoon' or 'any'.")
@func_parameter(
    "wants_different_time",
    "'true' only when the caller turned down the slot you offered without saying what they want instead. Otherwise 'false'.",
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
    if not idnv.is_verified(conv, idnv.STRICT):
        return idnv.require(conv, "reschedule_appointment", strength=idnv.STRICT)
    appt = appointments.selected(conv)
    if not appt:
        return (
            f"First find out which appointment they want to move.\n\n{move_state(conv)}"
        )

    req = move_request(conv)
    before = (req["preferred_date"], req["time_of_day"])
    if str(preferred_date or "").strip():
        req["preferred_date"] = str(preferred_date).strip()
    if str(time_of_day or "").strip().lower() in appointments.TIME_OF_DAY:
        req["time_of_day"] = str(time_of_day).strip().lower()
    rejected = str(wants_different_time).strip().lower() == "true"

    after = None
    if rejected and req["offer"]:
        req["rejected"] += 1
        conv.write_metric("RESCHEDULE_SLOT_REJECTED")
        if req["rejected"] >= appointments.MAX_REJECTED_OFFERS:
            conv.state.move_request = req
            return handoff(
                conv,
                "RESCHEDULE_SLOTS_REJECTED",
                "I'm sorry I couldn't find a time that suits. Let me put you through to our "
                "scheduling team, one moment please.",
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
        try:
            slot, note = appointments.find_slot(
                conv,
                req["preferred_date"],
                req["time_of_day"],
                appt.get("provider_id", ""),
                after,
            )
        except Exception:
            conv.log.error("open_slots failed", exc_info=True)
            slot = None
        if slot is None:
            conv.state.move_request = req
            return handoff(
                conv,
                "RESCHEDULE_NO_SLOTS_AVAILABLE",
                "I'm sorry, I can't see any open appointments right now. Let me put you through "
                "to our scheduling team, one moment please.",
            )
        req["offer"] = slot
    conv.state.move_request = req
    conv.write_metric("RESCHEDULE_SLOT_OFFERED")

    _text, mode = appointments.readback_text(conv, READBACK_KEY, move_fields(conv, req))
    appointments.mark_question(conv, READBACK_KEY)
    if mode == "none":
        return f"Nothing has changed. {move_question(conv, req, 'Ask again')}\n\n{move_state(conv)}"
    lead = f"{note} Offer only this slot. Ask" if note else "Offer only this slot. Ask"
    return f"{move_question(conv, req, lead)}\n\n{move_state(conv)}"
