from datetime import date, datetime, time

from _gen import *  # <AUTO GENERATED>
from functions.start_confirm_cancel_modify_flow import format_bookings
from functions.try_transfer_call import try_transfer_call


@func_description(
    "Should be called if the retrieved bookings don't match the details provided by the user"
)
@func_parameter(
    "booking_date",
    'The original date of the booking in YYYY-MM-DD format, or "-" if user didn\'t specify',
)
@func_parameter(
    "booking_time",
    'The original time of the booking in HH:MM format, or "-" if user didn\'t specify',
)
def booking_not_found(conv: Conversation, booking_date: str, booking_time: str):
    filtered_bookings = conv.state.bookings or []
    if booking_date != "-":
        filtered_bookings = [
            booking
            for booking in filtered_bookings
            if datetime.fromisoformat(booking.get("date_time")).date()
            == date.fromisoformat(booking_date)
        ]
    if booking_time != "-":
        filtered_bookings = [
            booking
            for booking in filtered_bookings
            if datetime.fromisoformat(booking.get("date_time")).time()
            == time.fromisoformat(booking_time)
        ]
    if filtered_bookings:
        formatted_bookings = format_bookings(filtered_bookings)
        return (
            f"This information seems to match these bookings:\n {formatted_bookings}."
        )
    return try_transfer_call(
        conv,
        "booking_not_found",
        "I can't see the booking, let me put you through to someone who can help, one second.",
        "default",
    )
