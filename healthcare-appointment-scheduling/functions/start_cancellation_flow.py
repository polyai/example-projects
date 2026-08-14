from typing import Any

import plog

from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Flow] Start cancelling an appointment. Verifies identity first if needed, then enters the Cancel Flow."
)
def start_cancellation_flow(conv: Conversation) -> dict[str, Any]:
    log_prefix = "[start_cancellation_flow]: "
    conv.write_metric("CANCEL_FLOW_INITIATED", True)

    if not getattr(conv.state, "identified_patient", None):
        plog.info(f"{log_prefix} no identified_patient, routing to IDNV first")
        conv.state.post_idnv_flow_name = "Cancel Flow"
        conv.goto_flow("IDNV")
        return {
            "content": (
                "Before we can cancel an appointment, we need to verify the caller's identity. "
                "Ask if the number they're calling from is the one on their account."
            )
        }

    conv.state.cancel_triage_done = False
    plog.info(f"{log_prefix} goto_flow='Cancel Flow'")
    conv.goto_flow("Cancel Flow")
    return {
        "content": (
            "You are now entering the Cancel Flow. "
            "The triage step will review conversation history and determine the right path."
        )
    }
