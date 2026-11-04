from _gen import *  # <AUTO GENERATED>
from datetime import date

import functions.api_client as api_client
import functions.appointments as appointments
import functions.idnv as idnv
from functions.handoff import handoff

KEY = "booking"
API_ERROR_UTTERANCE = (
    "I'm sorry, I couldn't complete that booking just now. I'll put you through to our "
    "scheduling team, who can help. One moment, please."
)


def done_line(appt: dict, today_) -> str:
    """'You're all booked in to see Dr. Smith on Thursday the 5th at 3:30pm. Is there
    anything else I can help with?'"""
    return (
        f"You're all booked in to see {appt['provider']} "
        f"{appointments.on_date(appt['date'], today_)} at {appointments.say_time(appt['start'])}. "
        f"{appointments.ANYTHING_ELSE}"
    )


@func_description(
    "Book the time the caller picked. Called without caller_confirmed it books nothing and returns what to read back. Call it with caller_confirmed 'true' once the caller agrees."
)
@func_parameter(
    "slot",
    "The time they picked, as 'YYYY-MM-DD HH:MM', exactly as update_booking_request gave it.",
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply agreed to the booking question for this slot (the readback this tool returned, or your offer that named the doctor, day and time). 'Okay', 'sure' or 'sounds good' to that question is agreement; an answer to something else, or real hesitation, is not.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me just book that in.", 3), ("Nearly there.", 3)],
)
def book_appointment(conv: Conversation, flow: Flow, slot: str, caller_confirmed: str):
    if not idnv.is_verified(conv, idnv.STRICT):
        return appointments.gate(conv, "book_appointment")
    if conv.state.booked_appointment_id:
        return "ALREADY BOOKED: don't book it again. For another appointment, call start_booking_flow."
    req = (
        conv.state.booking_request
        if isinstance(conv.state.booking_request, dict)
        else {}
    )
    if not req.get("type"):
        return (
            'NOT BOOKED: no appointment type yet. Ask "What\'s the appointment for?", then call '
            "update_booking_request."
        )
    parsed = appointments.parse_slot(slot)
    key = f"{parsed[0]} {parsed[1]}" if parsed else ""
    chosen = (req.get("slots") or {}).get(key)
    if not chosen:
        return (
            f"NOT BOOKED: '{slot}' isn't one of the free times update_booking_request gave. "
            "Call update_booking_request for that day and time first."
        )

    today_ = appointments.today(conv)
    fields = appointments.readback_fields(chosen, req["type"], today_)
    last = appointments.readback(conv, KEY) or {}
    if last.get("item") != key or last.get("fields") != fields:
        changed = appointments.mark_readback(conv, KEY, key, fields)
        return (
            f"NOT BOOKED YET: {appointments.read_back_text(fields, changed)}, then ask "
            f'"Shall I book that?" {appointments.CONSENT_HINT} Then call book_appointment '
            "again with the same slot and caller_confirmed 'true'."
        )
    if str(caller_confirmed or "").strip().lower() != "true":
        appointments.remark_turn(conv, KEY)
        return (
            "NOT BOOKED YET: the caller hasn't agreed yet. If they hesitated or asked something, "
            'answer or wait, then ask again ("Shall I go ahead and book it?"). Once they agree, '
            "call book_appointment again with the same slot and caller_confirmed 'true'."
        )
    if appointments.asked_this_turn(conv, KEY):
        return appointments.not_done_yet(fields, "book")

    patient = idnv.customer(conv) or {}
    try:
        if not appointments.slot_is_free(
            conv, chosen["provider_id"], chosen["date"], chosen["start"]
        ):
            appointments.forget_readback(conv, KEY)
            day_slots = api_client.open_slots(
                conv, date.fromisoformat(chosen["date"]), chosen["provider_id"], 1
            )
            req["slots"] = {
                **(req.get("slots") or {}),
                **{appointments.slot_key(s): s for s in day_slots},
            }
            req["slots"].pop(key, None)
            conv.state.booking_request = req
            times = ", ".join(
                f"{appointments.say_time(s['start'])} [{appointments.slot_key(s)}]"
                for s in day_slots
            )
            return (
                "NOT BOOKED: that time was taken before it could be booked. Say \"I'm sorry, "
                "that time's just been taken.\" and offer one or two of these, if any: "
                f"{times or 'none that day; call update_booking_request for another day'}."
            )
        appt = api_client.create_appointment(
            conv, patient["id"], chosen, req["type"], req.get("reason", "")
        )
    except Exception:
        conv.log.error("create_appointment failed", exc_info=True)
        conv.write_metric("BOOKING_FLOW_API_ERROR")
        return handoff(conv, "BOOKING_API_ERROR", API_ERROR_UTTERANCE)

    conv.state.booked_appointment_id = appt["id"]
    conv.state.visit_date = appt["date"]
    conv.state.booking_request = None
    conv.state.task = ""
    conv.write_metric("BOOKING_FLOW_APPOINTMENT_BOOKED")
    appointments.forget_readback(conv, KEY)
    conv.exit_flow()
    return {"utterance": done_line(appt, today_)}
