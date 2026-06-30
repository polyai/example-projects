import plog
from _gen import *  # <AUTO GENERATED>


def reschedule_entry(conv: Conversation, flow: Flow):
    """Reschedule Flow entry: route based on triage and caller-type state."""

    log_prefix = "[reschedule_entry]: "
    triage_done = getattr(conv.state, "reschedule_triage_done", False)
    plog.info(f"{log_prefix} reschedule_triage_done={triage_done}")

    if triage_done:
        plog.info(f"{log_prefix} triage already done, goto_step='Resolve Appointment'")
        flow.goto_step("Resolve Appointment", "Reschedule triage already done")
        return {"content": ("Ask the caller which appointment they would like to reschedule.")}

    caller_type_known = getattr(conv.state, "caller_is_case_manager", None) is not None
    if caller_type_known:
        plog.info(
            f"{log_prefix} triage not done (caller type known), goto_step='Triage Appointment Type'"
        )
        flow.goto_step(
            "Triage Appointment Type",
            "Fresh reschedule entry — caller type already known",
        )
        return {
            "content": (
                "Entering Reschedule Flow. Review conversation history"
                " to determine appointment type."
            )
        }

    plog.info(f"{log_prefix} triage not done, goto_step='Collect Caller Type'")
    flow.goto_step(
        "Collect Caller Type",
        "Fresh reschedule entry — collect caller type first",
    )
    return {"content": "Ask whether the caller is a patient or a case manager."}
