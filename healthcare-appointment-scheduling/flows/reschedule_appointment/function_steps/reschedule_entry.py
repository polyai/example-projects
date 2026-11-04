from _gen import *  # <AUTO GENERATED>
from functions import appointments


def reschedule_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the appointment to move (none, one or several)."""
    conv.state.task = "reschedule"
    gate = appointments.gate(conv, "reschedule_appointment")
    if gate:
        return gate

    conv.write_metric("RESCHEDULE_FLOW_INITIATED", write_once=True)
    flow.goto_step("Reschedule Appointment", "caller verified")
    picked = appointments.select_for_task(conv, "reschedule")
    if not conv.state.selected_appointment_id:
        return picked
    return (
        f"{picked} If the caller has already said when they'd like it instead, call "
        "find_new_time with that now. Otherwise say the appointment in a few words (\"That's "
        'your follow-up with Dr. Smith on Thursday the 5th at 10am.") and ask "When would suit '
        'you instead?"'
    )
