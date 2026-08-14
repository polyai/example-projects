from _gen import *  # <AUTO GENERATED>


@func_description("Save user phone number")
@func_parameter(
    "sms_phone_number", "the number to use (must have been confirmed by the user)"
)
def save_phone_number(conv: Conversation, flow: Flow, sms_phone_number: str):
    from flows.sms_flow.functions.validate_sms_phone_number import (
        cleanup_phone_number,
        is_phone_number_valid,
    )

    # phone_number = cleanup_number(phone_number) # in case LLM as inserted - when reading back
    sms_phone_number = cleanup_phone_number(
        sms_phone_number
    )  # in case LLM as inserted - when reading back

    if not is_phone_number_valid(sms_phone_number):
        flow.goto_step("SMS failed")
        return "Hmm, something doesn't seem to be working."

    conv.state.sms_phone_number = sms_phone_number
    flow.goto_step("Send SMS")
