from _gen import *  # <AUTO GENERATED>
from flows.change_booking.functions.update_booking_change import start_change
from functions import bookings, idnv


def change_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the booking to change (none, one or several)."""
    conv.state.task = "change"
    gate = idnv.require(conv, "change_booking")
    if gate:
        return gate

    conv.write_metric("CHANGE_BOOKING_FLOW_INITIATED", write_once=True)
    flow.goto_step("Change Booking", "caller verified")
    picked = bookings.select_for_task(conv, "change")
    booking = bookings.selected(conv)
    if not booking:
        return picked
    return f"{picked}\n\n{start_change(conv, booking)}".strip()
