"""Called when the caller identifies as a patient or case manager; sets state and continues to IDNV."""

import plog
from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the caller answers whether they are a patient or a case manager calling on behalf of a patient. Sets caller type state and routes to account lookup."
)
@func_parameter(
    "is_case_manager",
    "True if the caller is a case manager calling on behalf of a patient, False if the caller is the patient themselves.",
)
def caller_type_provided(conv: Conversation, flow: Flow, is_case_manager: bool):
    """Set caller type state variables and continue to IDNV entry."""
    log_prefix = "[caller_type_provided.caller_type_provided]: "
    plog.info(f"{log_prefix} is_case_manager={is_case_manager}")

    conv.state.caller_is_case_manager = is_case_manager
    conv.state.caller_is_patient = not is_case_manager

    caller_type = "case_manager" if is_case_manager else "patient"
    conv.write_metric("CALLER_TYPE", caller_type)
    plog.info(f"{log_prefix} caller_type='{caller_type}'")

    flow.goto_step("idnv_entry")
    return {}
