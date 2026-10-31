from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.appointments as appointments
import functions.idnv as idnv
from functions.handoff import handoff

READBACK_KEY = "cancel"


def _fields(conv, appt) -> list[tuple[str, str]]:
    return [("appointment", appointments.describe(appt, conv) if appt else "")]


def cancel_words(conv) -> str:
    """The cancel confirmation the caller hears: the appointment's type, day and
    time, named once."""
    appt = appointments.selected(conv)
    if not appt:
        return "Shall I cancel it, yes or no?"
    kind = (appt.get("type") or "appointment").lower()
    when = appointments.say_slot(appt, appointments.today(conv), provider=False)
    return f"Shall I cancel your {kind} on {when}, yes or no?"


def cancel_question(conv, lead: str = "Ask") -> str:
    return appointments.ask_yes_no(cancel_words(conv), lead)


def _cancel_state(conv, text: str) -> str:
    return appointments.call_state(
        conv,
        ["Task: cancel an appointment", f"Appointment: {text}"],
        "Wait for the caller's answer to the yes-or-no question about cancelling it. A clear yes "
        "means cancel it: call cancel_appointment with caller_confirmed='true'. 'Okay', 'mm-hm' "
        "or anything unclear is not a yes: ask the yes-or-no question again.",
    )


def cancel_readback(conv) -> str:
    appt = appointments.selected(conv)
    text, _mode = appointments.readback_text(conv, READBACK_KEY, _fields(conv, appt))
    appointments.mark_question(conv, READBACK_KEY)
    return f"{cancel_question(conv)}\n\n{_cancel_state(conv, text)}"


def cancellation_enabled(conv) -> bool:
    settings = (conv.real_time_config or {}).get("settings", {})
    return bool(settings.get("cancel_appointment_flow_enabled", True))


@func_description(
    "Cancel the appointment you read back, once the caller has said yes to cancelling it."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question about cancelling this appointment. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
)
@func_parameter(
    "reason", "Why they're cancelling, if they said. Empty string otherwise."
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Okay, cancelling that now.", 3), ("Just a moment.", 3)],
)
def cancel_appointment(
    conv: Conversation, flow: Flow, caller_confirmed: str, reason: str
):
    if not idnv.is_verified(conv, idnv.STRICT):
        return idnv.require(conv, "cancel_appointment", strength=idnv.STRICT)
    appt = appointments.selected(conv)
    if not appt:
        return "First find out which appointment they want to cancel."
    if not appointments.readback_is_current(conv, READBACK_KEY, _fields(conv, appt)):
        return cancel_readback(conv)
    if str(caller_confirmed).strip().lower() != "true":
        appointments.mark_question(conv, READBACK_KEY)
        return f"NOT CANCELLED YET. {cancel_question(conv, 'Ask again')}"
    if appointments.asked_this_turn(conv, READBACK_KEY):
        return appointments.NOT_DONE_YET
    if not cancellation_enabled(conv):
        return handoff(
            conv,
            "CANCEL_APPOINTMENT",
            "For cancellations I'll need to put you through to our scheduling team. One moment "
            "please.",
        )

    try:
        api_client.cancel_appointment(conv, appt["id"], str(reason or "").strip())
    except Exception:
        conv.log.error("cancel_appointment failed", exc_info=True)
        return handoff(
            conv,
            "CANCEL_API_ERROR",
            "I'm sorry, I couldn't cancel that just now. Let me put you through to our "
            "scheduling team, one moment please.",
        )

    if str(reason or "").strip():
        conv.write_metric("CANCEL_REASON", str(reason).strip()[:100])
    conv.write_metric("CANCEL_FLOW_COMPLETED")
    conv.state.selected_appointment_id = ""
    conv.state.task = ""
    appointments.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    return (
        "Cancelled. Tell the caller the appointment is cancelled, then ask if there's anything "
        "else."
    )
