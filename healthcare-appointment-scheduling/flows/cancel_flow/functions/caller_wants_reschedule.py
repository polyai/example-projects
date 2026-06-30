import plog
from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the caller accepts the reschedule offer in the cancel flow. Redirects to the Reschedule Flow."
)
def caller_wants_reschedule(conv: Conversation, flow: Flow) -> dict:
    log_prefix = "[caller_wants_reschedule.caller_wants_reschedule]: "
    plog.info(f"{log_prefix} caller accepted reschedule offer; goto_flow='Reschedule Flow'")
    conv.write_metric("CANCEL_DEFLECTED_TO_RESCHEDULE")
    conv.goto_flow("Reschedule Flow")
    return {"content": "Transition to the reschedule flow."}
