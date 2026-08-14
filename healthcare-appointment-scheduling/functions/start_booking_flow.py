from typing import Any

import plog

from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Flow] Start booking an appointment. Verifies identity first if needed, then enters the Booking Flow."
)
def start_booking_flow(conv: Conversation) -> dict[str, Any]:
    log_prefix = "[start_booking_flow]: "
    conv.write_metric("BOOKING_FLOW_INITIATED", True)

    if not getattr(conv.state, "identified_patient", None):
        plog.info(f"{log_prefix} no identified_patient, routing to IDNV first")
        conv.state.post_idnv_flow_name = "Booking Flow"
        conv.goto_flow("IDNV")
        return {
            "content": (
                "Before we can book an appointment, we need to verify the caller's identity. "
                "Ask if the number they're calling from is the one on their account."
            )
        }

    plog.info(f"{log_prefix} goto_flow='Booking Flow'")
    conv.goto_flow("Booking Flow")
    return {
        "content": (
            "You are now entering the Booking Flow. "
            "Do NOT speak yet — the flow will provide the next utterance."
        )
    }
