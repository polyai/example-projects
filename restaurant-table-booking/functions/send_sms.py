from _gen import *  # <AUTO GENERATED>
import re

from functions.util_functions import get_country_code_prefix


@func_description("Send SMS text")
@func_parameter("phone_number", "phone number to send the SMS to")
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=2,
    delay_responses=[("One moment while I send that...", 2)],
)
def send_sms(conv: Conversation, phone_number: str):
    valid, output = validate_phone_number(conv, phone_number)
    if not valid:
        return output
    conv.state.sms_phone_number = output
    try:
        conv.send_sms_template(output, conv.state.sms_template_id)
        return "SMS text sent successfully"
    except Exception:
        return "SMS text failed to send"


def validate_phone_number(conv, phone_number: str):
    # E.164 format
    pattern = r"^\+[1-9]\d{1,14}$"

    if not phone_number.startswith("+"):
        country_code = get_country_code_prefix(conv)
        phone_number.lstrip("0")
        phone_number = f"+{country_code}{phone_number}"

    if re.match(pattern, phone_number):
        return True, phone_number

    return (
        False,
        "It seems like the phone number might be invalid. Ask the user for their number again.",
    )
