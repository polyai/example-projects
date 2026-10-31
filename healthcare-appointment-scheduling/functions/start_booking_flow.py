from _gen import *  # <AUTO GENERATED>
from functions import idnv


@func_description(
    "The caller wants to book a new appointment (to see a doctor, a sick visit, a follow-up, a checkup). Call it as soon as that's clear, even if they're also giving details."
)
def start_booking_flow(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "BOOK_APPOINTMENT")
    conv.state.booking_request = None
    conv.state.booked_appointment_id = ""
    gate = idnv.require(conv, "book_appointment", strength=idnv.STRICT)
    if gate:
        return gate
    conv.goto_flow("book_appointment")
