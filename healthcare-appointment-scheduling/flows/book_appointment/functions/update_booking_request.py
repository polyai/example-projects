from _gen import *  # <AUTO GENERATED>
import functions.appointments as appointments
import functions.idnv as idnv


def _request(conv) -> dict:
    req = conv.state.booking_request
    if not isinstance(req, dict):
        req = {"type": "", "reason": "", "slots": {}}
    return dict(req)


@func_description(
    "Check when the patient's own provider is free for a new appointment. Call it once you know the type and when they'd like to come in (a day, a day and time, or the earliest), and again whenever they ask for another day. Don't say a time is free before it returns."
)
@func_parameter(
    "appointment_type",
    "'Sick visit' (a new problem), 'Follow-up' (a recheck of something already seen) or 'Wellness check' (a physical or check-up), worked out from what the caller said.",
)
@func_parameter("reason", "What it's for, in the caller's own words.")
@func_parameter(
    "preferred_date",
    "The day as YYYY-MM-DD from the date guide, or 'earliest' when they want the earliest available (never tomorrow's date for that).",
)
@func_parameter(
    "preferred_time",
    "A time the caller said, as HH:MM in 24-hour time (2pm is 14:00). Never one they didn't say.",
)
@func_parameter("day_said", "The caller's own words for the day, e.g. 'next Thursday'.")
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me just check what we've got.", 3), ("Nearly there.", 3)],
)
def update_booking_request(
    conv: Conversation,
    flow: Flow,
    appointment_type: str,
    reason: str,
    preferred_date: str,
    preferred_time: str,
    day_said: str,
):
    if not idnv.is_verified(conv, idnv.STRICT):
        return appointments.gate(conv, "book_appointment")
    if conv.state.booked_appointment_id:
        return (
            "ALREADY BOOKED: this appointment is booked; don't book it again. For another one, "
            "call start_booking_flow."
        )

    req = _request(conv)
    said_type = str(appointment_type or "").strip()
    new_type = appointments.normalise_type(said_type)
    if new_type:
        req["type"] = new_type
    if str(reason or "").strip():
        req["reason"] = str(reason).strip()[:200]
    conv.state.booking_request = req
    if not req["type"]:
        head = (
            f"NOT A TYPE: '{said_type}' isn't one of the three."
            if said_type
            else "NO TYPE YET."
        )
        return (
            f"{head} Unless they've said, ask \"What's the appointment for?\" and work the type out "
            "from the answer. Then call update_booking_request again."
        )
    if not str(preferred_date or "").strip():
        return (
            'Ask: "Would you like the earliest available, or a particular day and time?" Then '
            "call update_booking_request again with their answer."
        )

    patient = idnv.customer(conv) or {}
    kind = appointments.kind(req["type"])
    try:
        found = appointments.availability(
            conv,
            patient.get("provider_id", ""),
            preferred_date,
            preferred_time,
            day_said,
            question=f"Shall I book your {kind} for then?",
            handoff_reason="BOOKING_NO_SLOTS_AVAILABLE",
            walk_ins=req["type"] == "Sick visit",
        )
    except Exception:
        conv.log.error("open_slots failed", exc_info=True)
        conv.write_metric("BOOKING_FLOW_API_ERROR")
        return (
            "NOT CHECKED: the appointment system didn't answer. Say you're sorry, you can't see "
            "the diary just now, and offer to put them through to our scheduling team; if they "
            'agree, call handoff with reason="BOOKING_API_ERROR".'
        )

    slots = dict(req.get("slots") or {})
    slots.update({appointments.slot_key(s): s for s in found["slots"]})
    req["slots"] = slots
    conv.state.booking_request = req
    if found["slots"]:
        conv.write_metric("BOOKING_FLOW_SLOTS_OFFERED")
    offer = found["offer"]
    if offer:
        # The offer names the doctor, day and time and asks to book: it is the readback.
        fields = appointments.readback_fields(
            offer, req["type"], appointments.today(conv)
        )
        appointments.mark_readback(
            conv, "booking", appointments.slot_key(offer), fields, offer=True
        )
        return (
            f"{found['text']} {appointments.CONSENT_HINT} Then call book_appointment with that "
            "slot and caller_confirmed 'true'. If they pick another time, call book_appointment "
            "with it and caller_confirmed empty."
        )
    if found["slots"]:
        return (
            f"{found['text']} When they pick one, call book_appointment with its slot and "
            "caller_confirmed empty."
        )
    return found["text"]
