from _gen import *  # <AUTO GENERATED>
from functions import appointments


@func_description(
    "The caller wants a new appointment (to see a doctor, a sick visit, a follow-up, a check-up). Call it as soon as that's clear, even if they're also giving details."
)
def start_booking_flow(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "BOOK_APPOINTMENT")
    conv.state.booking_request = None
    conv.state.booked_appointment_id = ""
    appointments.forget_readback(conv, "booking")
    gate = appointments.gate(conv, "book_appointment")
    if gate:
        return gate
    conv.goto_flow("book_appointment")
    return "BOOKING: the caller is verified. Carry on with the booking."
