from _gen import *  # <AUTO GENERATED>
from functions.start_confirm_cancel_modify_flow import get_bookings_and_next_transition
from functions.try_transfer_call import try_transfer_call
from functions.util_functions import validate_phone_number


@func_description(
    'Save the user\'s phone number, including the country code and the "+" sign if relevant'
)
@func_parameter(
    "phone_number",
    'The phone number user provided, including any leading +. Do not add "+" or country code unless user said it.',
)
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=2,
    delay_responses=[("Let me have a look...", 3), ("One more moment...", 3)],
)
def save_phone_number_and_get_bookings(conv: Conversation, flow: Flow, phone_number: str):
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
        # We want VAD timeout when asking again for the phone number
        conv.state.use_vad_timeout = True
        return phone_number_validation
    if conv.state.calee_phone_number_validation:
        if phone_number_validation == conv.state.calee_phone_number_validation:
            return try_transfer_call(
                conv,
                "booking_not_found",
                "I can't find your booking, let me put you through to someone who can help.",
                "default",
            )
    conv.state.country_code, conv.state.phone_number = phone_number_validation
    res = get_bookings_and_next_transition(conv, user_provided_number=True)
    if isinstance(res, dict):
        if goto_step := res.get("transition", {}).get("goto_step", None):
            flow.goto_step(goto_step)
            del res["transition"]
    return res
