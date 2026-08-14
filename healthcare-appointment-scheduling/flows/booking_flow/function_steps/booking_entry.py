import plog

from _gen import *  # <AUTO GENERATED>


def booking_entry(conv: Conversation, flow: Flow):
    """Entry point for the Booking Flow. Routes to the new-patient check."""
    log_prefix = "[booking_entry]: "
    plog.info(f"{log_prefix} routing to Check New Patient")

    flow.goto_step("Check New Patient", "Start of booking flow")
    return {
        "content": "Check whether the caller is a new or existing patient at Poly Clinic."
    }
