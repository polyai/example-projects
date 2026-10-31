from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.bookings as bookings
import functions.idnv as idnv
from functions.handoff import handoff

READBACK_KEY = "cancel"


def _fields(conv, booking) -> list[tuple[str, str]]:
    return [("booking", bookings.describe_booking(conv, booking) if booking else "")]


def cancellation_enabled(conv) -> bool:
    """settings.cancel_booking_flow_enabled (default true): false sends cancellations to the team."""
    return bookings.is_true(
        str(bookings.setting(conv, "cancel_booking_flow_enabled", True))
    )


def cancel_question_text(conv, booking: dict) -> str:
    """'Shall I cancel your table for four people tomorrow at 7pm'."""
    table = bookings.short_table(
        conv, booking["party_size"], booking["date"], booking["time"]
    )
    return f"Shall I cancel your {table.removeprefix('a ')}"


def cancel_question(conv, booking: dict) -> str:
    return bookings.ask_yes_no(cancel_question_text(conv, booking))


def cancel_readback(conv) -> str:
    booking = bookings.selected(conv)
    text, _mode = bookings.readback_text(conv, READBACK_KEY, _fields(conv, booking))
    bookings.mark_asked(conv, READBACK_KEY)
    return (
        f"{cancel_question(conv, booking)} On a clear yes, call cancel_booking with "
        "caller_confirmed='true'.\n\n"
        + bookings.call_state(
            conv,
            ["Task: cancel a booking", f"Booking: {text}"],
            "Wait for a clear yes or no to cancelling it. 'Okay' or 'mm-hm' is not a yes: ask the "
            "yes-or-no question again.",
        )
    )


@func_description("Cancel the booking, once the caller has said yes to cancelling it.")
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question this tool's readback asked. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
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
    if not idnv.is_verified(conv):
        return idnv.require(conv, "cancel_reservation")
    booking = bookings.selected(conv)
    if not booking:
        return "First find out which booking they want to cancel, then call choose_booking."
    if not bookings.readback_is_current(conv, READBACK_KEY, _fields(conv, booking)):
        return cancel_readback(conv)
    if not bookings.is_true(caller_confirmed):
        bookings.mark_asked(conv, READBACK_KEY)
        return (
            f"NOT CANCELLED YET. {cancel_question(conv, booking)} On a clear yes, call "
            "cancel_booking again with caller_confirmed='true'."
        )
    if bookings.asked_this_turn(conv, READBACK_KEY):
        return bookings.not_done_yet(cancel_question_text(conv, booking))
    if not cancellation_enabled(conv):
        return handoff(
            conv,
            "CANCEL_BOOKING",
            "For cancellations I'll need to put you through to the team. One moment please.",
        )

    try:
        api_client.cancel_booking(conv, booking["id"], (reason or "").strip())
    except Exception:
        conv.log.error("cancel_booking failed", exc_info=True)
        return handoff(
            conv,
            "CANCEL_BOOKING_FAIL",
            "I'm sorry, I couldn't cancel that just now. Let me put you through to the team, one "
            "moment please.",
        )

    if reason and reason.strip():
        conv.write_metric("CANCEL_REASON", reason.strip()[:100])
    conv.write_metric("CANCEL_BOOKING_FLOW_SUCCESSFUL")
    conv.state.selected_booking_id = ""
    conv.state.task = ""
    bookings.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    return "Cancelled. Tell the caller the booking is cancelled, then ask if there's anything else."
