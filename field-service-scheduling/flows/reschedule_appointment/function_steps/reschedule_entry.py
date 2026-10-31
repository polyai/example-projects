from _gen import *  # <AUTO GENERATED>
from flows.reschedule_appointment.functions.find_new_time import move_state
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
    if not conv.state.selected_appointment_id:
        return f"{picked}\n\n{move_state(conv)}"
    return (
        f"{picked} If the caller has already said when they'd like it instead, call find_new_time "
        "with that now. Otherwise mention the visit briefly and ask when would suit them instead."
        f"\n\n{move_state(conv)}"
    )
