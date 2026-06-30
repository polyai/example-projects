from typing import Any

import plog
from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Flow] Start booking an appointment. Enters the Booking Flow, which handles identity verification internally after confirming the appointment category."
)
def start_booking_flow(conv: Conversation) -> dict[str, Any]:
    log_prefix = "[start_booking_flow.start_booking_flow]: "
    conv.write_metric("BOOKING_FLOW_INITIATED")
    plog.info(f"{log_prefix} goto_flow='Booking Flow'")
    conv.goto_flow("Booking Flow")
    return {
        "content": (
            "You are now entering the Booking Flow. "
            "Do NOT speak yet — do not say 'let me find appointment times' or anything similar. "
            "The flow will provide the next utterance (e.g. an insurance question)."
        )
    }
