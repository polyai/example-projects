from _gen import *  # <AUTO GENERATED>
from flows.cancel_appointment.functions.cancel_appointment import cancel_readback
from functions import appointments, idnv


def cancel_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the appointment to cancel (none, one or several)."""
    conv.state.task = "cancel"
    gate = idnv.require(conv, "cancel_appointment", strength=idnv.STRICT)
    if gate:
        return gate

    conv.write_metric("CANCEL_FLOW_INITIATED", write_once=True)
    flow.goto_step("Cancel Appointment", "caller verified")
    picked = appointments.select_for_task(conv, "cancel")
    if not conv.state.selected_appointment_id:
        return picked
    return cancel_readback(conv)
