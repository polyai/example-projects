from _gen import *  # <AUTO GENERATED>
from functions import idnv


@func_description(
    "The caller wants to change a booking they already have: the day, time, party size or a note."
)
def start_change_booking(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "CHANGE_BOOKING")
    conv.state.booking_change = None
    gate = idnv.require(conv, "change_booking")
    if gate:
        return gate
    conv.goto_flow("change_booking")
