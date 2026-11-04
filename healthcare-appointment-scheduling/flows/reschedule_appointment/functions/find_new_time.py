from _gen import *  # <AUTO GENERATED>
import functions.appointments as appointments
import functions.idnv as idnv


def move_request(conv) -> dict:
    req = conv.state.move_request
    if (
        not isinstance(req, dict)
        or req.get("appointment_id") != conv.state.selected_appointment_id
    ):
        req = {"appointment_id": conv.state.selected_appointment_id or "", "slots": {}}
    return dict(req)


@func_description(
    "Check when the provider is free for the appointment being moved. Call it once you know when they'd like it instead (a day, a day and time, or the earliest), and again whenever they ask for another day. Don't say a time is free before it returns."
)
@func_parameter(
    "preferred_date",
    "The day as YYYY-MM-DD from the date guide, or 'earliest' when they want the earliest available (never tomorrow's date for that).",
)
@func_parameter(
    "preferred_time",
    "A time the caller said, as HH:MM in 24-hour time (2pm is 14:00). Never one they didn't say.",
)
@func_parameter("day_said", "The caller's own words for the day, e.g. 'next Tuesday'.")
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me just check what we've got.", 3), ("Nearly there.", 3)],
)
def find_new_time(
    conv: Conversation,
    flow: Flow,
    preferred_date: str,
    preferred_time: str,
    day_said: str,
):
    if not idnv.is_verified(conv, idnv.STRICT):
        return appointments.gate(conv, "reschedule_appointment")
    appt = appointments.selected(conv)
    if not appt:
        return "First find out which appointment they want to move, then call choose_appointment."
    if not str(preferred_date or "").strip():
        return 'Ask: "When would suit you instead?" Then call find_new_time with their answer.'

    req = move_request(conv)
    kind = appointments.kind(appt["type"])
    try:
        found = appointments.availability(
            conv,
            appt.get("provider_id", ""),
            preferred_date,
            preferred_time,
            day_said,
            question=f"Shall I move your {kind} to then?",
            handoff_reason="RESCHEDULE_NO_SLOTS_AVAILABLE",
        )
    except Exception:
        conv.log.error("open_slots failed", exc_info=True)
        conv.write_metric("RESCHEDULE_FLOW_API_ERROR")
        return (
            "NOT CHECKED: the appointment system didn't answer. Say you're sorry, you can't see "
            "the diary just now, and offer to put them through to our scheduling team; if they "
            'agree, call handoff with reason="RESCHEDULE_API_ERROR".'
        )
    # The appointment's own time is never a new time for it.
    slots = [
        s
        for s in found["slots"]
        if (s["date"], s["start"]) != (appt["date"], appt["start"])
    ]
    req["slots"] = {
        **(req.get("slots") or {}),
        **{appointments.slot_key(s): s for s in slots},
    }
    conv.state.move_request = req
    if slots:
        conv.write_metric("RESCHEDULE_FLOW_SLOT_OFFERED")
    offer = found["offer"]
    if offer and offer in slots:
        fields = appointments.readback_fields(
            offer, appt["type"], appointments.today(conv), doctor=False
        )
        appointments.mark_readback(
            conv, "move", appointments.slot_key(offer), fields, offer=True
        )
        return (
            f"{found['text']} {appointments.CONSENT_HINT} Then call reschedule_appointment with "
            "that slot and caller_confirmed 'true'. If they pick another time, call "
            "reschedule_appointment with it and caller_confirmed empty."
        )
    if slots:
        return (
            f"{found['text']} When they pick one, call reschedule_appointment with its slot and "
            "caller_confirmed empty."
        )
    return found["text"]
