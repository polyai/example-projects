from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.bookings as bookings
import functions.idnv as idnv
from flows.change_booking.functions.update_booking_change import (
    _proposed,
    change_fields,
    change_question,
    change_state,
    is_different,
    pending_change,
    readback_key,
)
from functions.handoff import handoff


@func_description(
    "Save the change to the booking, once the caller has said yes to it. Saves exactly what the caller heard."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question this tool's readback asked. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Okay, updating that now.", 3), ("Just a moment.", 3)],
)
def modify_booking(conv: Conversation, flow: Flow, caller_confirmed: str):
    if not idnv.is_verified(conv):
        return idnv.require(conv, "change_booking")
    booking = bookings.selected(conv)
    if not booking:
        return "First find out which booking they want to change, then call choose_booking."
    change = pending_change(conv)
    if not change or not is_different(booking, change):
        return f"No change has been agreed yet. Ask what they'd like to change.\n\n{change_state(conv)}"

    proposed = _proposed(change)
    key = readback_key(booking["id"])
    fields = change_fields(conv, proposed)
    ask = bookings.ask_yes_no(change_question(conv, booking, change))
    on_yes = "On a clear yes, call modify_booking again with caller_confirmed='true'."
    if not bookings.readback_is_current(conv, key, fields):
        bookings.readback_text(conv, key, fields)
        bookings.mark_asked(conv, key)
        return f"NOT CHANGED YET. {ask} {on_yes}"
    if not bookings.is_true(caller_confirmed):
        bookings.mark_asked(conv, key)
        return f"NOT CHANGED YET. {ask} {on_yes}"
    if bookings.asked_this_turn(conv, key):
        return bookings.not_done_yet(change_question(conv, booking, change))

    # Re-check the new time still has room for the party before writing anything.
    day = bookings.parse_date(conv, proposed["date"])
    free = api_client.available_times(conv, day, proposed["party_size"], booking["id"])
    if proposed["time"] not in free:
        change["offer"] = None
        conv.state.booking_change = change
        return (
            "That time has just gone. Say so and call update_booking_change to find another."
            f"\n\n{change_state(conv)}"
        )

    try:
        updated = api_client.update_booking(conv, booking["id"], proposed)
    except Exception:
        conv.log.error("update_booking failed", exc_info=True)
        return handoff(
            conv,
            "MODIFY_BOOKING_FAIL",
            "I'm sorry, I couldn't change that booking just now. Let me put you through to the "
            "team, one moment please.",
        )

    conv.write_metric("CHANGE_BOOKING_FLOW_SUCCESSFUL")
    conv.state.booking_change = None
    conv.state.task = ""
    bookings.forget_readback(conv, key)
    conv.exit_flow()
    return (
        f"Done. Tell the caller their booking is now {bookings.describe_booking(conv, updated)}, "
        "then ask if there's anything else."
    )
