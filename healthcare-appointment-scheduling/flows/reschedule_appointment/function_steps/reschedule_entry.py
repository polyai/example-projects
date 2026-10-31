from _gen import *  # <AUTO GENERATED>
from flows.reschedule_appointment.functions.find_new_time import move_state
from functions import appointments, idnv


def reschedule_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the appointment to move (none, one or several)."""
    conv.state.task = "reschedule"
    gate = idnv.require(conv, "reschedule_appointment", strength=idnv.STRICT)
    if gate:
        return gate

    conv.write_metric("RESCHEDULE_FLOW_INITIATED", write_once=True)
    flow.goto_step("Reschedule Appointment", "caller verified")
    picked = appointments.select_for_task(conv, "reschedule")
    if not conv.state.selected_appointment_id:
        return f"{picked}\n\n{move_state(conv)}"
    return (
        f"{picked} If the caller has already said when they'd like it instead, call "
        "find_new_time with that now. Otherwise mention the appointment briefly and ask when "
        f"would suit them instead.\n\n{move_state(conv)}"
    )
