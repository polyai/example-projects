from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.bookings as bookings
import functions.existing_booking as existing
from functions.handoff import handoff
from functions.start_cancel_booking import CANCEL_TO_TEAM, cancellation_enabled


@func_description(
    "Cancel the booking. Call it once the caller agreed to the cancel question the entry gave you; without caller_confirmed it cancels nothing and returns the question again."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply agreed to the readback question this tool returned. 'Okay', 'sure' or 'sounds good' to that question is agreement; an answer to something else, or real hesitation, is not. Otherwise 'false'.",
)
@func_parameter(
    "reason", "Why they're cancelling, if they said. Empty string otherwise."
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Okay, cancelling that now.", 3), ("Just a moment.", 3)],
)
def cancel_booking(conv: Conversation, flow: Flow, caller_confirmed: str, reason: str):
    gate = bookings.require(conv, "cancel_reservation")
    if gate:
        return gate
    booking = bookings.selected(conv)
    if not booking:
        return "First find out which booking they want to cancel, then call choose_booking."
    fields = existing.cancel_fields(conv, booking)
    if not bookings.readback_is_current(conv, existing.CANCEL_KEY, fields):
        return existing.cancel_readback(conv)
    if not bookings.is_true(caller_confirmed):
        return f"NOT CANCELLED YET. {existing.cancel_readback(conv)}"
    if bookings.asked_this_turn(conv, existing.CANCEL_KEY):
        return bookings.not_done_yet(existing.cancel_sentence(conv, booking))
    if not cancellation_enabled(conv):
        return handoff(conv, "CANCEL_BOOKING", CANCEL_TO_TEAM)

    try:
        api_client.cancel_booking(conv, booking["id"], (reason or "").strip())
    except Exception:
        conv.log.error("cancel_booking failed", exc_info=True)
        return handoff(
            conv,
            "CANCEL_BOOKING_FAIL",
            "I'm sorry, I couldn't cancel that just now. Let me put you through to the team. One "
            "moment, please.",
        )

    if reason and reason.strip():
        conv.write_metric("CANCEL_REASON", reason.strip()[:100])
    conv.write_metric("CANCEL_BOOKING_FLOW_SUCCESSFUL")
    conv.state.selected_booking_id = ""
    conv.state.task = ""
    bookings.forget_readback(conv, existing.CANCEL_KEY)
    conv.exit_flow()
    line = (
        f"I've cancelled your booking for {bookings.short_when(conv, booking['date'], booking['time'])}. "
        "We hope to see you another time! Is there anything else I can help with?"
    )
    bookings.said_line(conv, line)
    return {"utterance": line}
