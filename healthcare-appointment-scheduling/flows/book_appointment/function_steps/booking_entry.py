from _gen import *  # <AUTO GENERATED>
from flows.book_appointment.functions.update_booking_request import request_state
from functions import appointments, idnv


def booking_entry(conv: Conversation, flow: Flow):
    """Entry gate: unverified callers go to verify_caller and come back here."""
    conv.state.task = "book"
    gate = idnv.require(conv, "book_appointment", strength=idnv.STRICT)
    if gate:
        return gate

    conv.write_metric("BOOKING_FLOW_INITIATED", write_once=True)
    flow.goto_step("Book Appointment", "caller verified")
    existing = appointments.upcoming(conv)
    note = ""
    if existing:
        note = (
            f"They already have {appointments.describe(existing[0], conv)}. Don't bring it up "
            "unless they seem to mean that appointment."
        )
    return (
        "Help the caller book an appointment. If they have already said what it's for or when "
        "suits, call update_booking_request with all of it now; otherwise ask what kind of "
        f"appointment they need (a sick visit, a follow-up or a wellness check). {note}"
        f"\n\n{request_state(conv)}"
    )
