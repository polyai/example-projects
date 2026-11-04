from _gen import *  # <AUTO GENERATED>
from functions import bookings


@func_description(
    "The caller wants to check the details of a booking they already have."
)
def start_check_booking(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "CHECK_BOOKING")
    gate = bookings.require(conv, "check_booking")
    if gate:
        return gate
    conv.goto_flow("check_booking")
