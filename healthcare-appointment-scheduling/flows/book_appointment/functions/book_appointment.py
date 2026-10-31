from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.appointments as appointments
import functions.idnv as idnv
from flows.book_appointment.functions.update_booking_request import (
    READBACK_KEY,
    book_question,
    booking_fields,
    booking_request,
    request_state,
)
from functions.handoff import handoff


@func_description(
    "Book the slot you offered, once the caller has clearly said yes to it. If anything changed since the caller last heard the details, this reads back only the change first."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question about booking this slot. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Okay, booking that in for you now.", 3), ("Just a moment.", 3)],
)
def book_appointment(conv: Conversation, flow: Flow, caller_confirmed: str):
    if not idnv.is_verified(conv, idnv.STRICT):
        return idnv.require(conv, "book_appointment", strength=idnv.STRICT)
    if conv.state.booked_appointment_id:
        return "This appointment is already booked; don't book it again. Ask if there's anything else."

    req = booking_request(conv)
    if not req["type"]:
        return f"Not ready to book: ask what kind of appointment they need.\n\n{request_state(conv)}"
    if not req.get("offer"):
        return f"No slot has been offered yet: call update_booking_request.\n\n{request_state(conv)}"

    fields = booking_fields(conv, req)
    if not appointments.readback_is_current(conv, READBACK_KEY, fields):
        appointments.readback_text(conv, READBACK_KEY, fields)
        appointments.mark_question(conv, READBACK_KEY)
        return (
            "NOT BOOKED YET: the caller hasn't heard these details. "
            f"{book_question(conv, req)}\n\n{request_state(conv)}"
        )
    if str(caller_confirmed).strip().lower() != "true":
        appointments.mark_question(conv, READBACK_KEY)
        return f"NOT BOOKED YET. {book_question(conv, req, 'Ask again')}\n\n{request_state(conv)}"
    if appointments.asked_this_turn(conv, READBACK_KEY):
        return appointments.NOT_DONE_YET

    patient = idnv.customer(conv)
    if not patient:  # verified above, so only a lost state gets here
        return idnv.require(conv, "book_appointment", strength=idnv.STRICT)
    try:
        appt = api_client.create_appointment(
            conv, patient["id"], req["offer"], req["type"], req["reason"]
        )
    except Exception:
        conv.log.error("create_appointment failed", exc_info=True)
        conv.write_metric("BOOKING_FLOW_API_ERROR")
        return handoff(
            conv,
            "BOOKING_API_ERROR",
            "I'm sorry, I couldn't complete that booking just now. Let me put you through to our "
            "scheduling team, one moment please.",
        )

    conv.state.booked_appointment_id = appt["id"]
    conv.state.booking_request = None
    conv.state.task = ""
    conv.write_metric("BOOKING_FLOW_APPOINTMENT_BOOKED")
    appointments.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    when = appointments.say_slot(appt, appointments.today(conv))
    return (
        f"Booked. Tell the caller they're all set for {when}. Don't repeat the other details or "
        "add advice. Then ask if there's anything else."
    )
