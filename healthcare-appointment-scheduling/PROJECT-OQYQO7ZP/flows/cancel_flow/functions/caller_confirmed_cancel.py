import plog
from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the caller confirms they want to cancel (not reschedule). Proceeds to appointment type triage."
)
def caller_confirmed_cancel(conv: Conversation, flow: Flow) -> dict:
    log_prefix = "[caller_confirmed_cancel.caller_confirmed_cancel]: "
    plog.info(f"{log_prefix} caller confirmed cancel; marking pushback done")
    conv.state.cancel_pushback_done = True
    conv.write_metric("CANCEL_PUSHBACK_DECLINED")

    caller_type_known = getattr(conv.state, "caller_is_case_manager", None) is not None
    if caller_type_known:
        flow.goto_step("Triage Appointment Type")
        return {"content": ("Review conversation history to determine the appointment department.")}

    flow.goto_step("Collect Caller Type")
    return {"content": "Ask whether the caller is a patient or a case manager."}
