import datetime as dt

from _gen import *  # <AUTO GENERATED>
from functions.get_bookings import get_bookings
from functions.start_function import set_datetime
from functions.try_transfer_call import try_transfer_call
from functions.util_functions import validate_phone_number
from functions.write_booking_metric import write_booking_metric


@func_description(
    "Initiate the confirm/cancel/modify process when the user wants to confirm, cancel, or modify a booking/reservation. You must call this again if the user wants to confirm, cancel or modify another booking/reservation."
)
@func_parameter("booking_intent", "user's intent (one of modify, cancel or confirm)")
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=4,
    delay_responses=[("Okay...", 1), ("Just checking if I can find your booking.", 3)],
)
def start_confirm_cancel_modify_flow(conv: Conversation, booking_intent: str):
    conv.state.cca_intent = booking_intent
    set_datetime(conv)

    if conv.state.disable_booking:
        return {
            "content": "Let the user know that making, changing, or cancelling bookings is not possible because this restaurant only accepts walk-in customers. Offer to help them with anything else."
        }

    if booking_intent == "confirm":
        write_booking_metric(conv, "INITIATED_CONFIRM", None, False)
    elif booking_intent == "modify":
        write_booking_metric(conv, "INITIATED_AMEND", None, False)
    elif booking_intent == "cancel":
        write_booking_metric(conv, "INITIATED_CANCEL", None, False)

    # This state variable is used in the send_sms flow to check if the
    # agent needs to go back to the CCA flow after sending an SMS
    # in the middle of the CCA flow

    conv.state.origin_flow = "confirm_cancel_modify_booking"
    if conv.caller_number:
        try:
            phone_number_validation = validate_phone_number(conv, conv.caller_number)
            conv.state.calee_phone_number_validation = phone_number_validation
            conv.state.country_code, conv.state.phone_number = phone_number_validation
            return get_bookings_and_next_transition(conv, user_provided_number=False)
        except Exception:
            pass
    # Check if the user's phone number is already saved
    if conv.state.phone_number and conv.state.country_code:
        return get_bookings_and_next_transition(conv, user_provided_number=True)

    conv.state.is_phone_number_collection = True
    return {
        "transition": {
            "goto_flow": "confirm_cancel_modify_booking",
            "goto_step": "Collect phone number",
        }
    }


def format_booking(booking):
    parsed_datetime = dt.datetime.fromisoformat(booking.get("date_time", ""))
    formatted_date = parsed_datetime.strftime("%A, %B %d, %Y")
    formatted_time = parsed_datetime.strftime("%H:%M")
    return (
        f"Date: {formatted_date}; "
        f"Time: {formatted_time}; "
        f"Party Size: {booking.get('party_size', 0)}; "
        f"Number of People: {booking.get('party_size', 0)}; "
        f"Special Requests: {booking.get('special_request', 'None')}; "
        f"Booking ID: {booking.get('reservation_id', '')}"
    )


def format_bookings(bookings):
    formatted_bookings = ""
    for booking in bookings:
        formatted_booking = format_booking(booking)
        formatted_bookings += formatted_booking + "\n\n"
    return formatted_bookings.strip()


def get_bookings_and_next_transition(conv, user_provided_number: bool):
    conv.state.bookings = get_bookings(
        conv=conv,
        phone_number=conv.state.phone_number,
        country_code=conv.state.country_code,
    )

    if conv.state.bookings is None:
        return try_transfer_call(
            conv,
            "lookup_booking_api_fail",
            "Hm, I’m having trouble finding this booking. Let me put you through to someone who can help, one second.",
            "default",
        )

    conv.state.formatted_bookings = format_bookings(conv.state.bookings)
    num_bookings = len(conv.state.bookings)
    next_step = None
    next_flow = "confirm_cancel_modify_booking"

    if num_bookings > 1:
        # If all bookings have experiences, we don't need to figure out which booking
        # the user wants to modify/cancel because we can't handle experience bookings
        if all(booking.get("experience_id") for booking in conv.state.bookings):
            if conv.state.cca_intent == "modify":
                return try_transfer_call(
                    conv,
                    "update_experience_booking",
                    "Hm, I found yout bookings, but can't change them here. Let me put you through to someone who can help, one second.",
                    "default",
                )
            if conv.state.cca_intent == "cancel":
                return try_transfer_call(
                    conv,
                    "cancel_experience_booking",
                    "Hm, I found yout bookings, but can't cancel them here. Let me put you through to someone who can help, one second.",
                    "default",
                )

        return {
            "content": f"You have saved the user's number (+{conv.state.country_code}{conv.state.phone_number}) and found multiple bookings under it, you need to determine which one they want to {conv.state.cca_intent}.",
            "transition": {"goto_step": "Determine booking", "goto_flow": next_flow},
        }
    elif num_bookings == 1:
        conv.state.booking = conv.state.bookings[0]
        conv.state.formatted_booking = format_booking(conv.state.bookings[0])
        if conv.state.cca_intent == "modify":
            if conv.state.booking.get("experience_id"):
                return try_transfer_call(
                    conv,
                    "update_experience_booking",
                    "Hm, I found your booking, but can't change it here. Let me put you through to someone who can help, one second.",
                    "default",
                )
            next_step = "Determine modifications"
        if conv.state.cca_intent == "cancel":
            if conv.state.booking.get("experience_id"):
                return try_transfer_call(
                    conv,
                    "cancel_experience_booking",
                    "Hm, I found your booking, but can't cancel it here. Let me put you through to someone who can help, one second.",
                    "default",
                )
            next_step = "Confirm cancellation"
        else:
            next_step = "Confirm details"
        return {
            "content": f"You have saved the user's phone number (+{conv.state.country_code}{conv.state.phone_number}), and found the user's booking under it.",
            "transition": {"goto_step": next_step, "goto_flow": next_flow},
        }
    else:
        if user_provided_number:
            if conv.state.user_provided_number_already_tried:
                return try_transfer_call(
                    conv,
                    "booking_not_found",
                    "I couldn't find your booking, let me put you through to someone who can help, one second.",
                    "default",
                )
            conv.state.user_provided_number_already_tried = True
            return {
                "utterance": "I couldn't find any bookings under your number. Do you have a different number?",
                "transition": {"goto_step": "Should try another number", "goto_flow": next_flow},
            }
        else:
            return {
                "utterance": "Could you please provide the phone number you used to make the booking?",
                "transition": {"goto_step": "Collect phone number", "goto_flow": next_flow},
            }
