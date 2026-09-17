import plog

from _gen import *  # <AUTO GENERATED>
from functions.readback import digits_only, spell_digits
from functions.start_sms_flow import offer_handoff_after_sms_failed

MIN_DIGITS = MAX_DIGITS = 10
DEFAULT_COUNTRY_CODE = 1


@func_description("Save the phone number to which the user wants to receive the SMS")
@func_parameter(
    "phone_number", "The phone number provided by the user (excluding the country code)"
)
@func_parameter(
    "country_code", 'Country code, without leading "+". Default to 0 if not provided.'
)
def phone_number_given(
    conv: Conversation, flow: Flow, phone_number: int, country_code: int
):
    log_prefix = "[phone_number_given]: "
    plog.info(
        f"{log_prefix} phone_number='{phone_number}', country_code='{country_code}'",
        is_pii=True,
    )
    if not country_code:
        country_code = DEFAULT_COUNTRY_CODE

    digits = digits_only(phone_number)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if not MIN_DIGITS <= len(digits) <= MAX_DIGITS:
        if conv.state.sms_number_retried:
            return offer_handoff_after_sms_failed(conv)
        conv.state.sms_number_retried = True
        conv.log.warning(
            "phone_number_given: invalid phone number length, re-asking",
            digit_count=len(digits),
        )
        if len(digits) < MIN_DIGITS:
            return {
                "utterance": (
                    "Sorry, I didn't quite catch the full number. Could you give me the "
                    "ten-digit number, starting with the area code? You can also type it on "
                    "your keypad, then press the pound key."
                )
            }
        return {
            "utterance": "Just so I'm sure, could you repeat that number one more time please?"
        }

    conv.state.sms_phone_number = "+" + str(country_code) + digits
    conv.state.phone_number_given_in_history = True

    return {
        "utterance": f"Thanks. Just to confirm, that was {spell_digits(digits)}, is that right?"
    }
