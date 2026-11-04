from _gen import *  # <AUTO GENERATED>
from functions import idnv, visits
from functions.choose_visit import check_line


def retrieve_appointments(conv: Conversation, flow: Flow):
    """Entry gate: verify, then look up the caller's upcoming visits."""
    conv.state.task = "confirm"
    gate = idnv.require(conv, "confirm_appointment")
    if gate:
        return gate

    conv.write_metric("CONFIRM_APPOINTMENT_FLOW_INITIATED", write_once=True)
    flow.goto_step("Confirm Visit", "caller verified")
    picked = visits.select_visit_for_task(conv, "confirm")
    visit = visits.selected_visit(conv)
    if visit:
        conv.write_metric("CONFIRM_APPOINTMENT_FLOW_SUCCESSFUL")
        return f'Read the visit back in one natural sentence, adding nothing: "{check_line(conv, visit)}"'
    return picked
