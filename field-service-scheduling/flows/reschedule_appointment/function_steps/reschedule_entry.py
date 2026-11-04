from _gen import *  # <AUTO GENERATED>
from flows.reschedule_appointment.functions.find_new_time import ASK_WHEN, move_state
from functions import idnv, visits


def reschedule_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the visit to move (none, one or several)."""
    conv.state.task = "reschedule"
    gate = idnv.require(conv, "reschedule_appointment")
    if gate:
        return gate

    conv.write_metric("MODIFY_APPOINTMENT_FLOW_INITIATED", write_once=True)
    flow.goto_step("Reschedule Visit", "caller verified")
    picked = visits.select_visit_for_task(conv, "reschedule")
    visit = visits.selected_visit(conv)
    if not visit:
        return f"{picked}\n\n{move_state(conv)}"
    said = visits.describe_visit(visit, conv).split(", for ")[0]
    return (
        f"{picked} If they've already said when they'd like it instead, call find_new_time with "
        "that now ('sooner' or 'as soon as possible' is preferred_date='earliest'). Otherwise "
        f"say: \"You've got {said}. {ASK_WHEN}\" (skip the first sentence if they've just heard "
        f"it).\n\n{move_state(conv)}"
    )
