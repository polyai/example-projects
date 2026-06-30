from typing import Any

import plog
from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Flow] Start rescheduling an appointment (triage appointment type, then Reschedule Flow)."
)
def start_rescheduling_flow(conv: Conversation) -> dict[str, Any]:
    log_prefix = "[start_rescheduling_flow.start_rescheduling_flow]: "

    conv.write_metric("RESCHEDULE_FLOW_INITIATED")
    conv.state.reschedule_triage_done = False

    plog.info(f"{log_prefix} goto_flow='Reschedule Flow'")
    conv.goto_flow("Reschedule Flow")
    return {
        "content": (
            "You are now entering the Reschedule Flow. "
            "The triage step will review conversation history and determine the right path."
        )
    }
