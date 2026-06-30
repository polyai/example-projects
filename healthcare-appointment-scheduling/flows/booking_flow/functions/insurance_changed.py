import plog
from _gen import *  # <AUTO GENERATED>

_LOG_PREFIX = "[insurance_changed]: "


@func_description(
    "Called when the caller says their insurance on file is no longer current. Routes to insurance name collection."
)
def insurance_changed(conv: Conversation, flow: Flow) -> dict:
    plog.info(f"{_LOG_PREFIX} caller says insurance changed")
    conv.write_metric("INSURANCE_CHANGED")
    flow.goto_step("Collect Insurance Name")
    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    if is_cm:
        return {"utterance": "No problem. What insurance plan does the patient have now?"}
    return {"utterance": "No problem. What insurance plan do you have now?"}
