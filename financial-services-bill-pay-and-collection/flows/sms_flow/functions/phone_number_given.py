import re

from functions.readback import spell_digits

from _gen import *  # <AUTO GENERATED>

KEY_NAME = "pound"
MIN_DIGITS = 10
MAX_DIGITS = 10
DEFAULT_COUNTRY_CODE = 1
GIVE_UP_UTTERANCE = (
    "I'm really sorry, but I'm not able to get this to send. "
    "Is there anything else I can help you with?"
)


@func_description("Save the phone number to which the user wants to receive the SMS")
@func_parameter(
    "phone_number",
    'The ten-digit phone number provided by the user, including the area code and excluding the country code. Digits only. Interpret "oh" as 0, e.g. "two oh one" = "201"',
)
@func_parameter(
    "country_code", 'Country code, without leading "+". Default to -1 if not provided.'
)
def phone_number_given(
    conv: Conversation, flow: Flow, phone_number: str, country_code: int
):
    if country_code == -1:
        country_code = DEFAULT_COUNTRY_CODE

    phone_number = re.sub(r"\D+", "", str(phone_number or ""))
    if len(phone_number) == 11 and phone_number.startswith("1"):
        phone_number = phone_number[1:]

    if len(phone_number) < MIN_DIGITS:
        if conv.state.sms_number_retried:
            conv.exit_flow()
            return {"utterance": GIVE_UP_UTTERANCE}
        conv.state.sms_number_retried = True
        return {
            "utterance": f"Sorry, I didn't quite catch the full number. Could you try again, or type it in on the keypad and press the {KEY_NAME} key?"
        }
    if len(phone_number) > MAX_DIGITS:
        if conv.state.sms_number_retried:
            conv.exit_flow()
            return {"utterance": GIVE_UP_UTTERANCE}
        conv.state.sms_number_retried = True
        return {
            "utterance": f"Just so I'm sure, could you type in that number on your keypad and press the {KEY_NAME} key when you're done?"
        }

    conv.state.sms_phone_number = "+" + str(country_code) + phone_number
    conv.state.phone_number_given_in_history = True
    return {
        "utterance": f"Thanks. Just to confirm, that was {spell_digits(phone_number)}, is that right?"
    }
