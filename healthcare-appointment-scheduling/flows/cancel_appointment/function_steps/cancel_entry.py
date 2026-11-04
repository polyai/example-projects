from _gen import *  # <AUTO GENERATED>
from functions import appointments


def cancel_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the appointment to cancel (none, one or several)."""
    conv.state.task = "cancel"
    gate = appointments.gate(conv, "cancel_appointment")
    if gate:
        return gate

    conv.write_metric("CANCEL_FLOW_INITIATED", write_once=True)
    flow.goto_step("Cancel Appointment", "caller verified")
    picked = appointments.select_for_task(conv, "cancel")
    if not conv.state.selected_appointment_id:
        return picked
    return appointments.cancel_readback(conv)
