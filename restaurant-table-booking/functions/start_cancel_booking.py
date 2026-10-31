from functions.handoff import handoff

from _gen import *  # <AUTO GENERATED>
from flows.cancel_reservation.functions.cancel_booking import cancellation_enabled
from functions import idnv


@func_description("The caller wants to cancel a booking they already have.")
def start_cancel_booking(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "CANCEL_BOOKING")
    if not cancellation_enabled(conv):
        return handoff(
            conv,
            "CANCEL_BOOKING",
            "For cancellations I'll need to put you through to the team. One moment please.",
        )
    gate = idnv.require(conv, "cancel_reservation")
    if gate:
        return gate
    conv.goto_flow("cancel_reservation")
