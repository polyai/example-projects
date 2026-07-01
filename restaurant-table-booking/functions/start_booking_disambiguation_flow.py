from _gen import *  # <AUTO GENERATED>


@func_description(
    'Called then the user did not explicitly say what they want to do with their booking (for example "a booking", "reservation, please")'
)
def start_booking_disambiguation_flow(conv: Conversation):
    if conv.state.disable_booking:
        return {
            "content": "Let the user know that making, changing, or cancelling bookings is not possible because this restaurant only accepts walk-in customers. Offer to help them with anything else."
        }

    conv.goto_flow("booking_disambiguation_flow")
