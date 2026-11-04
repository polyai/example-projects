from _gen import *  # <AUTO GENERATED>
from functions import appointments


def confirm_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then look up the caller's upcoming appointments."""
    conv.state.task = "confirm"
    gate = appointments.gate(conv, "confirm_appointment")
    if gate:
        return gate

    conv.write_metric("CONFIRM_FLOW_INITIATED", write_once=True)
    flow.goto_step("Confirm Appointment", "caller verified")
    picked = appointments.select_for_task(conv, "confirm")
    appt = appointments.selected(conv)
    if appt:
        conv.write_metric("CONFIRM_FLOW_COMPLETED")
        return (
            f'{picked} Say it in one natural sentence ("You\'ve got {appointments.describe(appt, conv)}."), '
            'adding nothing else, then ask "Is there anything you\'d like to change?"'
        )
    return picked
