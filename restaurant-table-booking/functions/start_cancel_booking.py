from _gen import *  # <AUTO GENERATED>
from functions import bookings
from functions.handoff import handoff

CANCEL_TO_TEAM = (
    "For cancellations I'll need to put you through to the team. One moment, please."
)


def cancellation_enabled(conv) -> bool:
    """settings.cancel_booking_flow_enabled (default true): false sends cancellations to the team."""
    return bookings.is_true(
        str(bookings.setting(conv, "cancel_booking_flow_enabled", True))
    )


@func_description("The caller wants to cancel a booking they already have.")
def start_cancel_booking(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "CANCEL_BOOKING")
    if not cancellation_enabled(conv):
        return handoff(conv, "CANCEL_BOOKING", CANCEL_TO_TEAM)
    gate = bookings.require(conv, "cancel_reservation")
    if gate:
        return gate
    conv.goto_flow("cancel_reservation")
