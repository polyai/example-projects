from _gen import *  # <AUTO GENERATED>
from functions.check_availability import handle_restaurant_closed
from functions.guest_search import is_guest_search_enabled, run_guest_search
from functions.start_function import set_datetime
from functions.start_handle_over_max_group_size import start_handle_over_max_group_size
from functions.write_booking_metric import write_booking_metric


@func_description(
    "Initiate the booking process when the user wants to make a booking/reservation"
)
@func_parameter(
    "party_size",
    "party size, if already specified by the user. Use 0 if the user didn't specify it yet.",
)
@func_parameter(
    "date",
    '(Optional) Date of the requested booking slot, which must be in the YYYY-MM-DD format, or "-" if unknown',
)
@func_parameter(
    "user_want_to_make_multiple_bookings",
    "(Optional) True when the user explicitly or implicitly requests multiple reservations in a single interaction",
)
def start_make_booking(
    conv: Conversation,
    party_size: int,
    date: str,
    user_want_to_make_multiple_bookings: bool,
):
    set_datetime(conv)

    # Check if restaurant is closed due to special date or regular opening hours
    if date != "-":
        if closed_prompt := handle_restaurant_closed(conv, date, "CREATE"):
            return closed_prompt

    if conv.state.disable_booking:
        return {
            "content": "Let the user know that making, changing, or cancelling bookings is not possible because this restaurant only accepts walk-in customers. Offer to help them with anything else."
        }

    if user_want_to_make_multiple_bookings:
        conv.state.make_multiple_bookings = True

    if conv.state.had_successful_booking:
        write_booking_metric(conv, "INITIATED_BOOKING_MULTIPLE", None, True)
    else:
        write_booking_metric(conv, "INITIATED_BOOKING", None, True)

    # Run Guest Search API if enabled for this variant and we don't already have results
    if is_guest_search_enabled(conv):
        phone = conv.state.get("phone_number")
        if (
            not conv.state.get("guest_search_name_hints")
            and phone
            and "@" not in phone
            and phone.lower() != "anonymous"
        ):
            try:
                run_guest_search(conv, phone_number=phone)
            except Exception as e:
                conv.log.error("Guest search failed in start_make_booking", error=e)

    if party_size >= int(conv.variant.large_party_size):
        return start_handle_over_max_group_size(conv, int(party_size))

    # This state variable is used in the send_sms flow to check if the
    # agent needs to go back to the booking flow after sending an SMS
    # in the middle of the booking flow
    if conv.current_flow == "make_booking":
        return "Continue with the booking process by calling functions or collecting information, but DO NOT call the start_make_booking function again for this booking!"
    conv.state.origin_flow = "make_booking"
    conv.goto_flow("make_booking")
    return
