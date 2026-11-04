from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.bookings as bookings
import functions.idnv as idnv
import functions.new_booking as nb
from functions.handoff import handoff


def _split_name(name: str) -> tuple[str, str]:
    first, _, last = name.strip().partition(" ")
    return first, last.strip()


def done_line(conv, booking: dict) -> str:
    """'Lovely, you're all booked for Friday at 8. Is there anything else I can help with?'"""
    when = bookings.short_when(conv, booking["date"], booking["time"])
    note = ", and I've added your note" if booking.get("notes") else ""
    return f"Lovely, you're all booked for {when}{note}. Is there anything else I can help with?"


@func_description(
    "Book the table. Call it without caller_confirmed first: it books nothing and returns what to read back. Call it with caller_confirmed 'true' once the caller agreed to that readback. It books exactly what the caller last heard."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply agreed to the readback question this tool returned. 'Okay', 'sure' or 'sounds good' to that question is agreement; an answer to something else, or real hesitation, is not. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[
        ("Lovely, booking that in for you now.", 3),
        ("Just a moment.", 3),
    ],
)
def finalize_booking(conv: Conversation, flow: Flow, caller_confirmed: str):
    if conv.state.booked_booking_id:
        return "This table is already booked; don't book it again. Ask if there's anything else."

    req = nb.booking_request(conv)
    if (
        not req.get("offer")
        or not req["name"]
        or not req["phone"]
        or not req["notes_answered"]
    ):
        return f"NOT BOOKED: {nb.next_step(conv, req)}\n\n{nb.request_state(conv, req)}"

    # Re-check the table is still free before writing anything.
    offer = req["offer"]
    day = bookings.parse_date(conv, offer["date"])
    if offer["time"] not in api_client.available_times(conv, day, req["party_size"]):
        result = bookings.check_table(conv, day, offer["time"], req["party_size"])
        req["offer"] = None
        req["offered"] = [f"{offer['date']}T{t}" for t in result.get("times", [])]
        nb.save(conv, req)
        return (
            "NOT BOOKED: that table was booked by someone else a moment ago. Say: \"I'm sorry, "
            f"that table's just been booked.\" Then: {result.get('say', '')}\n\n"
            + nb.request_state(conv, req)
        )

    fields = nb.fields(conv, req)
    if not bookings.readback_is_current(conv, nb.READBACK_KEY, fields):
        return nb.readback(conv, req)
    if not bookings.is_true(caller_confirmed):
        return nb.readback(conv, req)
    if bookings.asked_this_turn(conv, nb.READBACK_KEY):
        return bookings.not_done_yet(nb.full_sentence(conv, req))
    if conv.state.hesitated:
        # After "let me check with my wife", agreement to the wife isn't a yes to the
        # question: ask it again, and book on the answer to that.
        conv.state.hesitated = False
        bookings.mark_asked(conv, nb.READBACK_KEY)
        return {"utterance": nb.ASK_AGAIN}

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
            "team. One moment, please.",
        )

    conv.state.booked_booking_id = booking["id"]
    conv.state.booked_date = booking["date"]
    conv.state.booked_time = booking["time"]
    conv.write_metric("MAKE_BOOKING_FLOW_SUCCESSFUL")
    conv.write_metric("BOOKING_COVERS", booking["party_size"])
    bookings.forget_readback(conv, nb.READBACK_KEY)
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
    line = done_line(conv, booking)
    bookings.said_line(conv, line)
    return {"utterance": line}
