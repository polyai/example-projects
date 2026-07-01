from _gen import *  # <AUTO GENERATED>
from functions.make_booking_utils import _payment_requirement_accepted


@func_description(
    "Call this if the user is happy to give their payment details using the link in the SMS once the booking is completed."
)
@func_parameter("date", "Date of the requested booking slot, in YYYY-MM-DD format")
@func_parameter("time", "Time of the requested booking slot in HH:MM format, e.g. 15:00")
@func_parameter("party_size", "Party size for the booking")
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=4,
    delay_responses=[("Great.", 3), ("One moment.", 3)],
)
def payment_requirement_accepted(
    conv: Conversation, flow: Flow, date: str, time: str, party_size: int
):
    return _payment_requirement_accepted(conv, flow, date, time, party_size)
