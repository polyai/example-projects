import functions.new_booking as nb
from _gen import *  # <AUTO GENERATED>


def booking_entry(conv: Conversation, flow: Flow):
    """Entry: no verification for a new booking; hand over to the one booking step."""
    conv.write_metric("MAKE_BOOKING_FLOW_INITIATED", write_once=True)
    flow.goto_step("Make Booking", "booking started")
    return (
        "Help the caller book a table. First look at everything the caller has said so far: if "
        'it has a day, a time or a party size ("for twelve next Friday", "four of us at 7"), '
        "call update_booking_request with them now, in this same turn, with day_said in their "
        "words, before you say anything. If they gave a name, number or note, call "
        "update_booking_details with those too. Never ask for something they've already said. "
        'Only if they gave none of it, ask: "What day and time were you thinking of?"\n\n'
        + nb.request_state(conv)
    )
