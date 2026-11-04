import functions.existing_booking as existing

from _gen import *  # <AUTO GENERATED>
from functions import bookings
from functions.handoff import handoff

MAX_UNCLEAR = 3  # unclear answers to "which booking?" before the caller is put through


@func_description(
    "The caller has several upcoming bookings and you asked which one they mean. Call it with their answer, even if it doesn't pick one out."
)
@func_parameter(
    "booking_date",
    "The date of the booking they mean, as YYYY-MM-DD. Empty if they didn't say.",
)
@func_parameter(
    "booking_time", "Its time, 24-hour HH:MM, if they said. Empty otherwise."
)
def choose_booking(conv: Conversation, booking_date: str, booking_time: str):
    booking = bookings.choose(conv, booking_date, booking_time)
    if not booking:
        found = bookings.upcoming(conv)
        unclear = int(conv.state.booking_choice_unclear or 0) + 1
        conv.state.booking_choice_unclear = unclear
        conv.write_metric("BOOKING_CHOICE_UNCLEAR", unclear)
        if unclear >= MAX_UNCLEAR or not found:
            return handoff(
                conv,
                "BOOKING_CHOICE_UNCLEAR",
                "I'm sorry for the trouble. Let me put you through to the team, who can sort that "
                "out for you. One moment, please.",
            )
        # Nothing can be changed or cancelled until one booking is picked out clearly.
        conv.state.selected_booking_id = ""
        names = " or ".join(
            bookings.short_when(conv, b["date"], b["time"]) for b in found
        )
        return (
            f"NOT CHOSEN (attempt {unclear} of {MAX_UNCLEAR}): that doesn't pick out one booking. "
            f'Ask again which one: "Is it the one on {names}?" Then call choose_booking again with '
            "whatever they say, even if it doesn't pick one out."
        )

    conv.state.booking_choice_unclear = 0
    task = conv.state.task
    if task == "cancel":
        return existing.cancel_readback(conv)
    if task == "change":
        return existing.start_change(conv, booking)
    return existing.check_readback(conv, booking)
