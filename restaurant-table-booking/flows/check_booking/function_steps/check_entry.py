import functions.existing_booking as existing
from _gen import *  # <AUTO GENERATED>
from functions import bookings


def check_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then find the booking (none, one or several) and read it back."""
    conv.state.task = "check"
    gate = bookings.require(conv, "check_booking")
    if gate:
        return gate

    conv.write_metric("CHECK_BOOKING_FLOW_INITIATED", write_once=True)
    flow.goto_step("Check Booking", "caller verified")
    picked = bookings.select_for_task(conv, "check")
    booking = bookings.selected(conv)
    if not booking:
        return picked
    return existing.check_readback(conv, booking)
