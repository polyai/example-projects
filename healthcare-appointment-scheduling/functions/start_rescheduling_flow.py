from typing import Any

import plog

from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Flow] Start rescheduling an appointment. Verifies identity first if needed, then enters the Reschedule Flow."
)
def start_rescheduling_flow(conv: Conversation) -> dict[str, Any]:
    log_prefix = "[start_rescheduling_flow]: "
    conv.write_metric("RESCHEDULE_FLOW_INITIATED", True)

    if not getattr(conv.state, "identified_patient", None):
        plog.info(f"{log_prefix} no identified_patient, routing to IDNV first")
        conv.state.post_idnv_flow_name = "Reschedule Flow"
        conv.goto_flow("IDNV")
        return {
            "content": (
                "Before we can reschedule an appointment, we need to verify the caller's identity. "
                "Ask if the number they're calling from is the one on their account."
            )
        }

    conv.state.reschedule_triage_done = False
    plog.info(f"{log_prefix} goto_flow='Reschedule Flow'")
    conv.goto_flow("Reschedule Flow")
    return {
        "content": (
            "You are now entering the Reschedule Flow. "
            "The triage step will review conversation history and determine the right path."
        )
    }
