from _gen import *  # <AUTO GENERATED>


@func_description(
    "The caller wants to book a table. Call it as soon as that's clear, even if they're also giving details; the details are picked up from the conversation."
)
def start_make_booking(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "MAKE_BOOKING")
    if conv.current_flow == "make_booking" and not conv.state.booked_booking_id:
        return "You're already booking this table; carry on with update_booking_request and update_booking_details."
    conv.state.booking_request = None
    conv.state.booked_booking_id = ""
    conv.state.task = "book"
    conv.goto_flow("make_booking")
