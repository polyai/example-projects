from typing import Any

import plog
from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Flow] Start cancelling an appointment (triage appointment type, then Cancel Flow)."
)
def start_cancellation_flow(conv: Conversation) -> dict[str, Any]:
    log_prefix = "[start_cancellation_flow.start_cancellation_flow]: "

    conv.write_metric("CANCEL_FLOW_INITIATED")
    conv.state.cancel_triage_done = False

    plog.info(f"{log_prefix} goto_flow='Cancel Flow'")
    conv.goto_flow("Cancel Flow")
    return {
        "content": (
            "You are now entering the Cancel Flow. "
            "The triage step will review conversation history and determine the right path."
        )
    }
