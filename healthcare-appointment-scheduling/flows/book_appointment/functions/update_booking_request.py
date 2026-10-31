from _gen import *  # <AUTO GENERATED>
import functions.appointments as appointments
import functions.idnv as idnv
from functions.handoff import handoff

READBACK_KEY = "booking"


def booking_request(conv) -> dict:
    req = conv.state.booking_request
    if not isinstance(req, dict):
        req = {
            "type": "",
            "reason": "",
            "preferred_date": "",
            "time_of_day": "any",
            "offer": None,
            "rejected": 0,
        }
    return dict(req)


def booking_fields(conv, req: dict) -> list[tuple[str, str]]:
    offer = req.get("offer") or {}
    kind = (req["type"] or "appointment").lower()
    return [
        ("what", f"a {kind}" + (f" for {req['reason']}" if req["reason"] else "")),
        (
            "when",
            f"on {appointments.say_slot(offer, appointments.today(conv))}"
            if offer
            else "",
        ),
    ]


def book_words(conv, req: dict) -> str:
    """The booking confirmation the caller hears: the action, the type and the
    slot (day, time, doctor). The reason is left out."""
    kind = (req["type"] or "appointment").lower()
    when = appointments.say_slot(req["offer"], appointments.today(conv))
    return f"Shall I book your {kind} for {when}, yes or no?"


def book_question(conv, req: dict, lead: str = "Ask") -> str:
    return appointments.ask_yes_no(book_words(conv, req), lead)


def request_state(conv) -> str:
    req = booking_request(conv)
    offer = req.get("offer")
    today = appointments.today(conv)
    lines = [
        "Task: book a new appointment",
        "Type: " + (req["type"] or "not given"),
        "Reason: " + (req["reason"] or "not given (optional)"),
        "When suits: "
        + (req["preferred_date"] or "earliest available")
        + ("" if req["time_of_day"] == "any" else f", {req['time_of_day']}"),
        "Offered: " + (appointments.say_slot(offer, today) if offer else "nothing yet"),
    ]
    if not req["type"]:
        nxt = "Ask what kind of appointment they need: a sick visit, a follow-up or a wellness check."
    elif offer:
        nxt = (
            "Wait for the caller's answer to the yes-or-no question about booking this slot. A "
            "clear yes means book it: call book_appointment with caller_confirmed='true'. 'Okay', "
            "'mm-hm' or anything unclear is not a yes: ask the yes-or-no question again."
        )
    else:
        nxt = "Call update_booking_request to get a slot to offer."
    return appointments.call_state(conv, lines, nxt)


@func_description(
    "Save what the caller has told you about the appointment they want, and get the next slot to offer once you know the appointment type. Call it whenever they give or change any detail, or turn down the slot you offered."
)
@func_parameter(
    "appointment_type",
    "One of: Sick visit (any new problem the caller describes: 'a new health issue', an illness, an injury, symptoms, pain), Follow-up (a recheck or follow-up on something already seen), Wellness check (annual physical, checkup, screening). Pick it yourself from what they said; empty string only if they haven't said what it's for.",
)
@func_parameter(
    "reason",
    "What it's for in the caller's own words, e.g. 'sore throat'. Empty string if not said.",
)
@func_parameter(
    "preferred_date",
    "The day they asked for, as YYYY-MM-DD from the date guide; for a range, its first day ('next week' is the Monday the guide names). 'any' only if they don't mind which day or want the earliest. Empty if not said.",
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
def update_booking_request(
    conv: Conversation,
    flow: Flow,
    appointment_type: str,
    reason: str,
    preferred_date: str,
    time_of_day: str,
    wants_different_time: str,
):
    if not idnv.is_verified(conv, idnv.STRICT):
        return idnv.require(conv, "book_appointment", strength=idnv.STRICT)
    if conv.state.booked_appointment_id:
        return (
            "This appointment is already booked. If the caller wants to change it, call "
            "start_rescheduling_flow."
        )

    req = booking_request(conv)
    before = (req["preferred_date"], req["time_of_day"])
    said_type = str(appointment_type or "").strip()
    kind = appointments.normalise_type(said_type)
    type_changed = bool(kind) and kind != req["type"]
    if kind:
        req["type"] = kind
    # Code only checks the type is one of the three; it never works one out.
    unknown_type = not kind and said_type.lower() not in ("", "na", "none")
    if str(reason or "").strip() and str(reason).strip().lower() not in ("na", "none"):
        req["reason"] = str(reason).strip()
    if str(preferred_date or "").strip():
        req["preferred_date"] = str(preferred_date).strip()
    if str(time_of_day or "").strip().lower() in appointments.TIME_OF_DAY:
        req["time_of_day"] = str(time_of_day).strip().lower()

    rejected = str(wants_different_time).strip().lower() == "true"
    preference_changed = before != (req["preferred_date"], req["time_of_day"])
    after = None
    if rejected and req["offer"]:
        req["rejected"] += 1
        conv.write_metric("BOOKING_SLOT_REJECTED")
        if req["rejected"] >= appointments.MAX_REJECTED_OFFERS:
            conv.state.booking_request = req
            return handoff(
                conv,
                "BOOKING_SLOTS_REJECTED",
                "I'm sorry I couldn't find a time that suits. Let me put you through to our "
                "scheduling team, one moment please.",
            )
        after = req["offer"]

    if unknown_type or not req["type"]:
        conv.state.booking_request = req
        head = (
            f"NOT A TYPE: '{said_type}' is not one of the three."
            if unknown_type
            else "NO TYPE YET."
        )
        return (
            f"{head} Ask what kind of appointment they need: a sick visit, a follow-up or a "
            "wellness check. Then call update_booking_request again with their answer."
            f"\n\n{request_state(conv)}"
        )

    note = ""
    if rejected or preference_changed or not req["offer"]:
        patient = idnv.customer(conv) or {}
        try:
            slot, note = appointments.find_slot(
                conv,
                req["preferred_date"],
                req["time_of_day"],
                patient.get("provider_id", ""),
                after,
            )
        except Exception:
            conv.log.error("open_slots failed", exc_info=True)
            slot = None
        if slot is None:
            conv.state.booking_request = req
            return handoff(
                conv,
                "BOOKING_NO_SLOTS_AVAILABLE",
                "I'm sorry, I can't see any open appointments right now. Let me put you through "
                "to our scheduling team, one moment please.",
            )
        req["offer"] = slot
    conv.state.booking_request = req
    conv.write_metric("BOOKING_SLOT_OFFERED")

    _text, mode = appointments.readback_text(
        conv, READBACK_KEY, booking_fields(conv, req)
    )
    appointments.mark_question(conv, READBACK_KEY)
    if mode == "none" and not type_changed:
        return f"Nothing has changed. {book_question(conv, req, 'Ask again')}\n\n{request_state(conv)}"
    lead = f"{note} Offer only this slot. Ask" if note else "Offer only this slot. Ask"
    return f"{book_question(conv, req, lead)}\n\n{request_state(conv)}"
