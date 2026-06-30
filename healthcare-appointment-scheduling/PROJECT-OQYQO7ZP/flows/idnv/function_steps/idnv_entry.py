"""Route on flow entry: no caller number -> Collect Phone; else Check Phone Number."""

import plog
from _gen import *  # <AUTO GENERATED>


def idnv_entry(conv: Conversation, flow: Flow):
    """Run on IDNV flow entry; route to Collect Phone Number or Check Phone Number."""
    log_prefix = "[idnv_entry]: "
    plog.info(f"{log_prefix} caller_number='{conv.caller_number}'", is_pii=True)
    conv.write_metric("IDNV_FLOW_INITIATED")
    if not conv.caller_number:
        conv.log.info("IDNV entry: no caller_number, routing to Collect Phone Number")
        flow.goto_step("Collect Phone Number", "No caller ID")
        return {"content": ("Ask the user what phone number we can use to look up their account.")}
    flow.goto_step("Check Phone Number", "Caller ID identified")
    if getattr(conv.state, "caller_is_case_manager", False):
        return {
            "content": (
                "Tell the user you'll need to verify the patient's identity"
                " and ask if the number they're calling from is the one on"
                " file for the patient's account."
            )
        }
    return {
        "content": (
            "Tell the user you'll need to pull up their account and ask "
            "if the number they're calling from is the one on their account."
        )
    }
