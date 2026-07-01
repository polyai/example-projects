from _gen import *  # <AUTO GENERATED>
from functions.start_confirm_cancel_modify_flow import format_booking
from functions.try_transfer_call import try_transfer_call
from functions.write_booking_metric import write_booking_metric


def find_booking(conv: Conversation, booking_id: str):
    for booking in conv.state.bookings or []:
        if booking.get("reservation_id") == booking_id:
            return booking
    return None


@func_description(
    "Call this once you have determined the booking id for the requested booking. This will start the modification process."
)
@func_parameter("booking_id", "The booking id of the identified booking")
def booking_identified(conv: Conversation, flow: Flow, booking_id: str):
    booking = find_booking(conv=conv, booking_id=booking_id)

    if not booking:
        return "That booking ID doesn't exist, please try again to determine the booking."

    conv.state.booking = booking
    conv.state.formatted_booking = format_booking(booking)
    if conv.state.cca_intent == "modify":
        if booking.get("experience_id"):
            return try_transfer_call(
                conv,
                "update_experience_booking",
                "Hm, I’m having trouble changing that booking. Let me put you through to someone who can help, one second.",
                "default",
            )
        flow.goto_step("Determine modifications")
        return "You have saved the user's phone number, and found the user's booking."
    if conv.state.cca_intent == "cancel":
        if booking.get("experience_id"):
            return try_transfer_call(
                conv,
                "cancel_experience_booking",
                "Hm, I’m having trouble cancelling that booking. Let me put you through to someone who can help, one second.",
                "default",
            )
        flow.goto_step("Confirm cancellation")
        return "You have saved the user's phone number, and found the user's booking."
    if conv.state.cca_intent == "confirm":
        write_booking_metric(conv, "SUCCESSFUL_CONFIRM", None, False)
        flow.goto_step("Confirm details")
        return "You have saved the user's phone number, and found the user's booking."
