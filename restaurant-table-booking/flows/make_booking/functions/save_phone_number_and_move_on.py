from _gen import *  # <AUTO GENERATED>
from functions.guest_search import is_guest_search_enabled, run_guest_search
from functions.try_transfer_call import try_transfer_call
from functions.util_functions import validate_phone_number


@func_description(
    'Save the user\'s phone number, including the country code and the "+" if relevant'
)
@func_parameter(
    "phone_number",
    'The phone number user provided, including any leading +. Do not add "+" unless user said it.',
)
def save_phone_number_and_move_on(conv: Conversation, flow: Flow, phone_number: str):
    previous_number = conv.state.phone_number
    previous_country_code = conv.state.country_code

    try:
        phone_number_validation = validate_phone_number(conv, phone_number)
    except Exception:
        return try_transfer_call(
            conv,
            "phone_number_collection_failed",
            "I am having some trouble with that phone number, let me put you through to someone who can help.",
            "default",
        )
    if isinstance(phone_number_validation, str):
        return phone_number_validation
    conv.state.country_code, conv.state.phone_number = phone_number_validation
    # bookings with cancellation policy need a mobile number
    conv.state.is_landline_number = (
        conv.state.phone_number
        and conv.state.country_code == 44
        and conv.state.phone_number[0] != "7"
    )
    if conv.state.is_landline_number is True and conv.state.cancellation_type:
        return try_transfer_call(
            conv,
            "phone_number_collection_failed_landline",
            "I am having some trouble with that phone number, let me put you through to someone who can help.",
            "default",
        )
    # Re-run guest search only if the phone number changed from what we already had
    if is_guest_search_enabled(conv):
        new_number = f"+{conv.state.country_code}{conv.state.phone_number}"
        if (
            new_number != previous_number
            and new_number != f"+{previous_country_code}{previous_number}"
        ):
            try:
                run_guest_search(conv, phone_number=new_number)
            except Exception as e:
                conv.state.guest_search_name_hints = None
                conv.state.guest_search_candidates = None
                conv.state.guest_search_primary = None
                conv.log.error("Guest search failed after new phone collection", error=e)

    conv.state.origin_step = "Final details"
    flow.goto_step("Final details")

    conv.state.additional_booking_final_details = None
    conv.write_metric("CREATE_BOOKING_PHONE_NUMBER_COLLECTED")

    return "You have saved the users phone number, you can now make the booking."
