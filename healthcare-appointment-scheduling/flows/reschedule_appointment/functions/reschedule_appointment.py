from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.appointments as appointments
import functions.idnv as idnv
from flows.reschedule_appointment.functions.find_new_time import (
    READBACK_KEY,
    move_fields,
    move_question,
    move_request,
    move_state,
)
from functions.handoff import handoff


@func_description(
    "Move the appointment to the slot you offered, once the caller has clearly said yes to it. If anything changed since the caller last heard the details, this reads back only the change first."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question about moving it to this slot. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
)
@func_parameter(
    "reason", "Why they're moving it, if they said. Empty string otherwise."
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Okay, moving that for you now.", 3), ("Just a moment.", 3)],
)
def reschedule_appointment(
    conv: Conversation, flow: Flow, caller_confirmed: str, reason: str
):
    if not idnv.is_verified(conv, idnv.STRICT):
        return idnv.require(conv, "reschedule_appointment", strength=idnv.STRICT)
    appt = appointments.selected(conv)
    req = move_request(conv)
    if not appt:
        return (
            f"First find out which appointment they want to move.\n\n{move_state(conv)}"
        )
    if not req.get("offer"):
        return f"No new slot offered yet: call find_new_time.\n\n{move_state(conv)}"

    fields = move_fields(conv, req)
    if not appointments.readback_is_current(conv, READBACK_KEY, fields):
        appointments.readback_text(conv, READBACK_KEY, fields)
        appointments.mark_question(conv, READBACK_KEY)
        return (
            "NOT MOVED YET: the caller hasn't heard these details. "
            f"{move_question(conv, req)}\n\n{move_state(conv)}"
        )
    if str(caller_confirmed).strip().lower() != "true":
        appointments.mark_question(conv, READBACK_KEY)
        return f"NOT MOVED YET. {move_question(conv, req, 'Ask again')}\n\n{move_state(conv)}"
    if appointments.asked_this_turn(conv, READBACK_KEY):
        return appointments.NOT_DONE_YET

    try:
        api_client.move_appointment(conv, appt["id"], req["offer"])
    except Exception:
        conv.log.error("move_appointment failed", exc_info=True)
        return handoff(
            conv,
            "RESCHEDULE_API_ERROR",
            "I'm sorry, I couldn't move that appointment just now. Let me put you through to our "
            "scheduling team, one moment please.",
        )

    if str(reason or "").strip():
        conv.write_metric("RESCHEDULE_REASON", str(reason).strip()[:100])
    conv.write_metric("RESCHEDULE_FLOW_COMPLETED")
    conv.state.move_request = None
    conv.state.task = ""
    appointments.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    when = appointments.say_slot(req["offer"], appointments.today(conv))
    return (
        f"Moved. Tell the caller their {appt['type'].lower()} is now {when}. Then ask if there's "
        "anything else."
    )
