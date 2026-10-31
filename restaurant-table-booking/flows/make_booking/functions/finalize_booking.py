from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.bookings as bookings
import functions.idnv as idnv
from flows.make_booking.functions.update_booking_request import (
    READBACK_KEY,
    book_question,
    booking_fields,
    booking_request,
    confirm_booking,
    missing_details,
    next_step,
    request_state,
)
from functions.handoff import handoff


def _split_name(name: str) -> tuple[str, str]:
    first, _, last = name.strip().partition(" ")
    return first, last.strip()


@func_description(
    "Book the table, once the caller has said yes to booking it. Books exactly what the caller heard; if anything changed since, it asks again first."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question this tool's readback asked. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Okay, booking that in for you now.", 3), ("Just a moment.", 3)],
)
def finalize_booking(conv: Conversation, flow: Flow, caller_confirmed: str):
    if conv.state.booked_booking_id:
        return "This table is already booked; don't book it again. Ask if there's anything else."

    req = booking_request(conv)
    if (
        missing_details(req)
        or not req.get("offer")
        or not req["name"]
        or not req["phone"]
    ):
        return f"Not ready to book: {next_step(conv, req)}\n\n{request_state(conv)}"

    # Re-check the table is still free for this party before writing anything.
    day = bookings.parse_date(conv, req["offer"]["date"])
    free = api_client.available_times(conv, day, req["party_size"])
    if req["offer"]["time"] not in free:
        found, note = bookings.find_time(
            conv, day, req["offer"]["time"], req["party_size"], declined=req["declined"]
        )
        req["offer"] = {"date": req["offer"]["date"], "time": found} if found else None
        conv.state.booking_request = req
        if not found:
            return f"That time has just gone. {note}\n\n{request_state(conv)}"

    fields = booking_fields(conv, req)
    ask = bookings.ask_yes_no(book_question(conv, req))
    on_yes = "On a clear yes, call finalize_booking again with caller_confirmed='true'."
    if not bookings.readback_is_current(conv, READBACK_KEY, fields):
        return f"NOT BOOKED YET. {confirm_booking(conv, req)} {on_yes}\n\n{request_state(conv)}"
    if not bookings.is_true(caller_confirmed):
        bookings.mark_asked(conv, READBACK_KEY)
        return f"NOT BOOKED YET. {ask} {on_yes}\n\n{request_state(conv)}"
    if bookings.asked_this_turn(conv, READBACK_KEY):
        return bookings.not_done_yet(book_question(conv, req))

    offer = req["offer"] or {}
    first, last = _split_name(req["name"])
    try:
        booking = api_client.create_booking(
            conv,
            {"first_name": first, "last_name": last, "phone": req["phone"]},
            offer["date"],
            offer["time"],
            req["party_size"],
            req["notes"],
        )
    except Exception:
        conv.log.error("create_booking failed", exc_info=True)
        return handoff(
            conv,
            "MAKE_BOOKING_FAIL",
            "I'm sorry, I couldn't complete that booking just now. Let me put you through to the "
            "team, one moment please.",
        )

    conv.state.booked_booking_id = booking["id"]
    conv.write_metric("MAKE_BOOKING_FLOW_SUCCESSFUL")
    conv.write_metric("BOOKING_COVERS", booking["party_size"])
    bookings.forget_readback(conv, READBACK_KEY)
    # The caller just gave the name and number on this booking, which is the lax ID&V
    # standard, so they can change it on this call without being asked again.
    if not idnv.is_verified(conv) and not idnv.has_failed(conv):
        idnv.verify_lax(
            conv,
            booking["phone"],
            req["name"],
            lookup=lambda phone: api_client.find_guests_by_phone(conv, phone),
        )
    conv.exit_flow()
    when = bookings.say_when(conv, booking["date"], booking["time"])
    return (
        f"Booked. Tell the caller they're all set for {when}. Don't repeat the other details. "
        "Then ask if there's anything else."
    )
