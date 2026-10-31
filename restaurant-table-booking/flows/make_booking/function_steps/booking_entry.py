from _gen import *  # <AUTO GENERATED>
from flows.make_booking.functions.update_booking_request import request_state


def booking_entry(conv: Conversation, flow: Flow):
    """Entry: no verification for a new booking; hand over to the one booking step."""
    conv.write_metric("MAKE_BOOKING_FLOW_INITIATED", write_once=True)
    flow.goto_step("Make Booking", "booking started")
    return (
        "Help the caller book a table. If they have already given the party size, day or time, "
        "call update_booking_request with them now, and if they gave a name, number or note, "
        "call update_booking_details with those too; otherwise ask when they'd like to come in "
        f"and how many people.\n\n{request_state(conv)}"
    )
