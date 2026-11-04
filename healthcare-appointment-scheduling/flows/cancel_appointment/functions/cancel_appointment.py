from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.appointments as appointments
import functions.idnv as idnv
from functions.handoff import handoff

KEY = "cancel"
API_ERROR_UTTERANCE = (
    "I'm sorry, I couldn't cancel that just now. I'll put you through to our scheduling team, "
    "who can help. One moment, please."
)
DISABLED_UTTERANCE = "For cancellations I'll need to put you through to our scheduling team. One moment, please."


def cancellation_enabled(conv) -> bool:
    settings = (conv.real_time_config or {}).get("settings", {})
    return bool(settings.get("cancel_appointment_flow_enabled", True))


def done_line(appt: dict, today_) -> str:
    """'I've cancelled your follow-up on Thursday the 5th. Is there anything else I can help
    with?'"""
    day = appointments.short_date(appt["date"], today_)
    when = "for tomorrow" if day == "tomorrow" else f"on {day}"
    return f"I've cancelled your {appointments.kind(appt['type'])} {when}. {appointments.ANYTHING_ELSE}"


@func_description(
    "Cancel the appointment you read back, once the caller has agreed to cancelling it."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply agreed to the question about cancelling this appointment that this tool or the flow gave you. 'Okay', 'sure' or 'go ahead' to that question is agreement; an answer to something else, or real hesitation, is not.",
)
@func_parameter("reason", "Why they're cancelling, if they said. Never ask for one.")
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me just cancel that for you.", 3), ("Nearly there.", 3)],
)
def cancel_appointment(
    conv: Conversation, flow: Flow, caller_confirmed: str, reason: str
):
    if not cancellation_enabled(conv):
        return handoff(conv, "CANCEL_APPOINTMENT", DISABLED_UTTERANCE)
    if not idnv.is_verified(conv, idnv.STRICT):
        return appointments.gate(conv, "cancel_appointment")
    appt = appointments.selected(conv)
    if not appt:
        return "First find out which appointment they want to cancel, then call choose_appointment."
    fields = appointments.cancel_fields(conv, appt)
    last = appointments.readback(conv, KEY) or {}
    if last.get("item") != appt["id"] or last.get("fields") != fields:
        return appointments.cancel_readback(conv)
    if str(caller_confirmed or "").strip().lower() != "true":
        appointments.remark_turn(conv, KEY)
        return (
            "NOT CANCELLED: the caller hasn't agreed yet. If they hesitated or asked something, "
            'answer or wait, then ask again ("Shall I cancel that for you?"). If they\'d rather '
            "move it, call start_rescheduling_flow; if they'd like to keep it, say \"No problem, "
            "your appointment's still booked.\""
        )
    if appointments.asked_this_turn(conv, KEY):
        return appointments.not_done_yet(fields, "cancel")

    try:
        api_client.cancel_appointment(conv, appt["id"], str(reason or "").strip())
    except Exception:
        conv.log.error("cancel_appointment failed", exc_info=True)
        conv.write_metric("CANCEL_FLOW_API_ERROR")
        return handoff(conv, "CANCEL_API_ERROR", API_ERROR_UTTERANCE)

    if str(reason or "").strip():
        conv.write_metric("CANCEL_REASON", str(reason).strip()[:100])
    conv.write_metric("CANCEL_FLOW_COMPLETED")
    conv.state.selected_appointment_id = ""
    conv.state.task = ""
    appointments.forget_readback(conv, KEY)
    conv.exit_flow()
    return {"utterance": done_line(appt, appointments.today(conv))}
