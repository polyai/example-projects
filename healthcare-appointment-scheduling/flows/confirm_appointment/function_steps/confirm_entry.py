from _gen import *  # <AUTO GENERATED>
from functions import appointments, idnv


def confirm_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then look up the caller's upcoming appointments."""
    conv.state.task = "confirm"
    gate = idnv.require(conv, "confirm_appointment", strength=idnv.STRICT)
    if gate:
        return gate

    conv.write_metric("CONFIRM_FLOW_INITIATED", write_once=True)
    flow.goto_step("Confirm Appointment", "caller verified")
    picked = appointments.select_for_task(conv, "confirm")
    appt = appointments.selected(conv)
    if appt:
        conv.write_metric("CONFIRM_FLOW_COMPLETED")
        return (
            f"Read the appointment back in one natural sentence: {appointments.describe(appt, conv)}. "
            "Then ask if there's anything else you can help with."
        )
    return picked
