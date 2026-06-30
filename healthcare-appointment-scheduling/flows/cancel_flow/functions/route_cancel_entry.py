import plog
from _gen import *  # <AUTO GENERATED>


@func_description(
    "Entry routing for the Cancel Flow. Routes to Triage Appointment Type on first entry, or directly to Resolve Appointment when returning from identity verification."
)
def route_cancel_entry(conv: Conversation, flow: Flow) -> dict:
    log_prefix = "[route_cancel_entry.route_cancel_entry]: "
    triage_done = getattr(conv.state, "cancel_triage_done", False)
    plog.info(f"{log_prefix} cancel_triage_done={triage_done}")

    if triage_done:
        plog.info(f"{log_prefix} triage already done, goto_step='Resolve Appointment'")
        flow.goto_step("Resolve Appointment")
        return {"content": "Ask the caller which appointment they would like to cancel."}

    plog.info(f"{log_prefix} first entry, goto_step='Reschedule Pushback'")
    flow.goto_step("Reschedule Pushback")
    return {"content": "Offer the caller the option to reschedule instead of cancel."}
