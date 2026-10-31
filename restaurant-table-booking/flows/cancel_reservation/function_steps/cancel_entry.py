from _gen import *  # <AUTO GENERATED>
from flows.cancel_reservation.functions.cancel_booking import cancel_readback
from functions import bookings, idnv


def cancel_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the booking to cancel (none, one or several)."""
    conv.state.task = "cancel"
    gate = idnv.require(conv, "cancel_reservation")
    if gate:
        return gate

    conv.write_metric("CANCEL_BOOKING_FLOW_INITIATED", write_once=True)
    flow.goto_step("Cancel Booking", "caller verified")
    picked = bookings.select_for_task(conv, "cancel")
    if not conv.state.selected_booking_id:
        return picked
    return f"{picked}\n\n{cancel_readback(conv)}".strip()
