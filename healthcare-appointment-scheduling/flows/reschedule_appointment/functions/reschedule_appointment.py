from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.appointments as appointments
import functions.idnv as idnv
from functions.handoff import handoff

KEY = "move"
API_ERROR_UTTERANCE = (
    "I'm sorry, I couldn't move that appointment just now. I'll put you through to our "
    "scheduling team, who can help. One moment, please."
)


def done_line(appt: dict, slot: dict, today_) -> str:
    """'I've moved your follow-up to Tuesday the 10th at 2pm. Is there anything else I can
    help with?'"""
    return (
        f"I've moved your {appointments.kind(appt['type'])} to "
        f"{appointments.short_date(slot['date'], today_)} at "
        f"{appointments.say_time(slot['start'])}. {appointments.ANYTHING_ELSE}"
    )


@func_description(
    "Move the appointment to the time the caller picked. Called without caller_confirmed it moves nothing and returns what to read back. Call it with caller_confirmed 'true' once the caller agrees."
)
@func_parameter(
    "slot", "The new time, as 'YYYY-MM-DD HH:MM', exactly as find_new_time gave it."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply agreed to the question about moving it to this slot (the readback this tool returned, or your offer that named the day and time). 'Okay', 'sure' or 'sounds good' to that question is agreement; an answer to something else, or real hesitation, is not.",
)
@func_parameter("reason", "Why they're moving it, if they said.")
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me just move that for you.", 3), ("Nearly there.", 3)],
)
def reschedule_appointment(
    conv: Conversation, flow: Flow, slot: str, caller_confirmed: str, reason: str
):
    if not idnv.is_verified(conv, idnv.STRICT):
        return appointments.gate(conv, "reschedule_appointment")
    appt = appointments.selected(conv)
    if not appt:
        return "First find out which appointment they want to move, then call choose_appointment."
    req = conv.state.move_request if isinstance(conv.state.move_request, dict) else {}
    parsed = appointments.parse_slot(slot)
    key = f"{parsed[0]} {parsed[1]}" if parsed else ""
    chosen = (
        (req.get("slots") or {}).get(key)
        if req.get("appointment_id") == appt["id"]
        else None
    )
    if not chosen:
        return (
            f"NOT MOVED: '{slot}' isn't one of the free times find_new_time gave. Call "
            "find_new_time for that day and time first."
        )

    today_ = appointments.today(conv)
    fields = appointments.readback_fields(chosen, appt["type"], today_, doctor=False)
    item = f"{appt['id']} {key}"
    last = appointments.readback(conv, KEY) or {}
    if last.get("item") not in (item, key) or last.get("fields") != fields:
        changed = appointments.mark_readback(conv, KEY, item, fields)
        return (
            f"NOT MOVED YET: {appointments.read_back_text(fields, changed)}, then ask "
            f'"Shall I move it?" {appointments.CONSENT_HINT} Then call reschedule_appointment '
            "again with the same slot and caller_confirmed 'true'."
        )
    if str(caller_confirmed or "").strip().lower() != "true":
        appointments.remark_turn(conv, KEY)
        return (
            "NOT MOVED YET: the caller hasn't agreed yet. If they hesitated or asked something, "
            'answer or wait, then ask again ("Shall I go ahead and move it?"). Once they agree, '
            "call reschedule_appointment again with the same slot and caller_confirmed 'true'."
        )
    if appointments.asked_this_turn(conv, KEY):
        return appointments.not_done_yet(fields, "move")

    try:
        if not appointments.slot_is_free(
            conv, chosen["provider_id"], chosen["date"], chosen["start"]
        ):
            appointments.forget_readback(conv, KEY)
            return (
                "NOT MOVED: that time was taken before it could be moved. Say \"I'm sorry, that "
                "time's just been taken.\" Then call find_new_time for that day again and offer "
                "what it returns."
            )
        api_client.move_appointment(conv, appt["id"], chosen)
    except Exception:
        conv.log.error("move_appointment failed", exc_info=True)
        conv.write_metric("RESCHEDULE_FLOW_API_ERROR")
        return handoff(conv, "RESCHEDULE_API_ERROR", API_ERROR_UTTERANCE)

    if str(reason or "").strip():
        conv.write_metric("RESCHEDULE_REASON", str(reason).strip()[:100])
    conv.write_metric("RESCHEDULE_FLOW_COMPLETED")
    conv.state.visit_date = chosen["date"]
    conv.state.move_request = None
    conv.state.task = ""
    appointments.forget_readback(conv, KEY)
    conv.exit_flow()
    return {"utterance": done_line(appt, chosen, today_)}
