from _gen import *  # <AUTO GENERATED>
from functions import bookings, idnv


def check_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then find the booking (none, one or several) and read it back."""
    conv.state.task = "check"
    gate = idnv.require(conv, "check_booking")
    if gate:
        return gate

    conv.write_metric("CHECK_BOOKING_FLOW_INITIATED", write_once=True)
    flow.goto_step("Check Booking", "caller verified")
    picked = bookings.select_for_task(conv, "check")
    booking = bookings.selected(conv)
    if not booking:
        return picked
    return f"{picked}\n\n{check_readback(conv, booking)}".strip()


def check_readback(conv, booking: dict) -> str:
    conv.write_metric("CHECK_BOOKING_FLOW_SUCCESSFUL")
    name = f"{booking['first_name']} {booking['last_name']}".strip()
    return (
        f"Read the booking back in one natural sentence: {bookings.describe_booking(conv, booking)}, "
        f"under {name}. Then ask if there's anything they'd like to change.\n\n"
        + bookings.call_state(
            conv,
            [
                "Task: check a booking",
                f"Booking: {bookings.describe_booking(conv, booking)}",
            ],
            "Answer any question about it. To change it call start_change_booking; to cancel "
            "it call start_cancel_booking.",
        )
    )
