from _gen import *  # <AUTO GENERATED>
from functions import appointments


def booking_entry(conv: Conversation, flow: Flow):
    """Entry gate: unverified callers go to verify_caller and come back here."""
    conv.state.task = "book"
    gate = appointments.gate(conv, "book_appointment")
    if gate:
        return gate

    conv.write_metric("BOOKING_FLOW_INITIATED", write_once=True)
    flow.goto_step("Book Appointment", "caller verified")
    return (
        "BOOKING: if the caller has already said what it's for or when suits, call "
        "update_booking_request with all of it now. Otherwise ask \"What's the appointment "
        "for?\" Don't bring up any appointment they already have."
    )
