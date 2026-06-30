import plog
from _gen import *  # <AUTO GENERATED>


@func_description(
    "Entry routing for the Reschedule Flow. Routes to Triage Appointment Type on first entry, or directly to Resolve Appointment when returning from identity verification."
)
def route_reschedule_entry(conv: Conversation, flow: Flow) -> dict:
    log_prefix = "[route_reschedule_entry.route_reschedule_entry]: "
    triage_done = getattr(conv.state, "reschedule_triage_done", False)
    plog.info(f"{log_prefix} reschedule_triage_done={triage_done}")

    if triage_done:
        plog.info(f"{log_prefix} triage already done, goto_step='Resolve Appointment'")
        flow.goto_step("Resolve Appointment")
        return {"content": "Ask the caller which appointment they would like to reschedule."}

    plog.info(f"{log_prefix} first entry, goto_step='Triage Appointment Type'")
    flow.goto_step("Triage Appointment Type")
    return {"content": "Review conversation history to determine the appointment department."}
