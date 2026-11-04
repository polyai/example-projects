from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.bookings as bookings
import functions.existing_booking as existing
from functions.handoff import handoff


@func_description(
    "Save the change to the booking. Call it once the caller agreed to the question update_booking_change gave you; without caller_confirmed it saves nothing and returns the question again. Saves exactly what the caller heard."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply agreed to the readback question this tool returned. 'Okay', 'sure' or 'sounds good' to that question is agreement; an answer to something else, or real hesitation, is not. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Okay, updating that now.", 3), ("Just a moment.", 3)],
)
def modify_booking(conv: Conversation, flow: Flow, caller_confirmed: str):
    gate = bookings.require(conv, "change_booking")
    if gate:
        return gate
    booking = bookings.selected(conv)
    if not booking:
        return "First find out which booking they want to change, then call choose_booking."
    change = existing.pending_change(conv)
    if (
        not change
        or not change.get("offer")
        or not existing.is_different(booking, change)
    ):
        return f'Nothing has been agreed yet. Ask: "What would you like to change?"\n\n{existing.change_state(conv)}'

    proposed = existing.proposed(change)
    key = existing.change_key(booking["id"])
    fields = existing.change_fields(conv, proposed)
    question = existing.change_question(conv, booking, change)
    on_yes = "A yes, or an acknowledgement to it, is a yes: call modify_booking with caller_confirmed='true'."
    if not bookings.readback_is_current(conv, key, fields) or not bookings.is_true(
        caller_confirmed
    ):
        bookings.readback_changes(conv, key, fields)
        bookings.mark_asked(conv, key)
        return f'NOT CHANGED YET. Ask: "{question}" {on_yes}'
    if bookings.asked_this_turn(conv, key):
        return bookings.not_done_yet(question)

    # Re-check the new time still has room for the party before writing anything.
    day = bookings.parse_date(conv, proposed["date"])
    free = api_client.available_times(conv, day, proposed["party_size"], booking["id"])
    if proposed["time"] not in free:
        change["offer"] = None
        conv.state.booking_change = change
        return (
            "NOT CHANGED: that table was booked by someone else a moment ago. Say \"I'm sorry, "
            "that table's just been booked.\" and call update_booking_change to find another."
            f"\n\n{existing.change_state(conv)}"
        )

    try:
        updated = api_client.update_booking(conv, booking["id"], proposed) or {
            **booking,
            **proposed,
        }
    except Exception:
        conv.log.error("update_booking failed", exc_info=True)
        return handoff(
            conv,
            "MODIFY_BOOKING_FAIL",
            "I'm sorry, I couldn't change that booking just now. Let me put you through to the "
            "team. One moment, please.",
        )

    conv.write_metric("CHANGE_BOOKING_FLOW_SUCCESSFUL")
    conv.state.booking_change = None
    conv.state.task = ""
    conv.state.booked_date = updated["date"]
    conv.state.booked_time = updated["time"]
    bookings.forget_readback(conv, key)
    conv.exit_flow()
    line = existing.change_done(conv, updated, booking)
    bookings.said_line(conv, line)
    return {"utterance": line}
