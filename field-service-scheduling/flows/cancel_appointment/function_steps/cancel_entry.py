from _gen import *  # <AUTO GENERATED>
from flows.cancel_appointment.functions.cancel_visit import cancel_readback
from functions import idnv, visits


def cancel_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the visit to cancel (none, one or several)."""
    conv.state.task = "cancel"
    gate = idnv.require(conv, "cancel_appointment")
    if gate:
        return gate

    conv.write_metric("CANCEL_APPOINTMENT_FLOW_INITIATED", write_once=True)
    flow.goto_step("Cancel Visit", "caller verified")
    picked = visits.select_visit_for_task(conv, "cancel")
    if not conv.state.selected_appointment_id:
        return picked
    return cancel_readback(conv)
