import functions.existing_booking as existing
from _gen import *  # <AUTO GENERATED>
from functions import bookings


def change_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the booking to change (none, one or several)."""
    conv.state.task = "change"
    gate = bookings.require(conv, "change_booking")
    if gate:
        return gate

    conv.write_metric("CHANGE_BOOKING_FLOW_INITIATED", write_once=True)
    flow.goto_step("Change Booking", "caller verified")
    picked = bookings.select_for_task(conv, "change")
    booking = bookings.selected(conv)
    if not booking:
        return picked
    return existing.start_change(conv, booking)
