from _gen import *  # <AUTO GENERATED>


@func_description("Save the phone number to which the user wants to receive the SMS")
@func_parameter(
    "phone_number",
    'The phone number provided by the user (excluding the country code). Digits only. Include the initial 0 if and only if the user specifies it in the input. Interpret "oh" as 0, e.g. "oh 7" = "07"',
)
@func_parameter(
    "country_code", 'Country code, without leading "+". Default to -1 if not provided.'
)
def phone_number_given(
    conv: Conversation, flow: Flow, phone_number: str, country_code: int
):
    # regional constants
    KEY_NAME = "pound" if conv.language == "en-US" else "hash"
    MIN_DIGITS = 10 if conv.language == "en-US" else 9
    MAX_DIGITS = 10 if conv.language == "en-US" else 11
    DEFAULT_COUNTRY_CODE = 1

    if country_code == -1:
        country_code = DEFAULT_COUNTRY_CODE

    import re

    phone_number = re.sub(r"\D+", "", phone_number)

    # length validation
    if len(phone_number) < MIN_DIGITS:
        if conv.state.sms_number_retried:
            conv.exit_flow()
            if conv.language in ["en-US", "en-GB"]:
                return {
                    "utterance": "I'm really sorry, but I'm not able to get this to send. Is there anything else I can help you with?"
                }
            return "Tell the user that you're having trouble getting the phone number, and ask if there's anything else you can help them with."
        conv.state.sms_number_retried = True
        if conv.language in ["en-US", "en-GB"]:
            return {
                "utterance": f"Sorry, I didn't quite catch the full number. Could you try again, or type it in on the keypad and press the {KEY_NAME} key?"
            }
        return f"Ask the user to say that number again, or to type it in on their keypad and press the {KEY_NAME} when they're done."
    if len(phone_number) > MAX_DIGITS:
        if conv.state.sms_number_retried:
            conv.exit_flow()
            if conv.language in ["en-US", "en-GB"]:
                return {
                    "utterance": "I'm really sorry, but I'm not able to get this to send. Is there anything else I can help you with?"
                }
            return "Tell the user that you're having trouble getting the phone number, and ask if there's anything else you can help them with."
        conv.state.sms_number_retried = True
        if conv.language in ["en-US", "en-GB"]:
            return {
                "utterance": f"Just so I'm sure, could you type in that number on your keypad and press the {KEY_NAME} key when you're done?"
            }
        return f"Ask the user to say that number again, or to type it in on their keypad and press the {KEY_NAME} when they're done."

    if phone_number.startswith("0"):
        conv.state.sms_phone_number = "+" + str(country_code) + phone_number[1:]
    else:
        conv.state.sms_phone_number = "+" + str(country_code) + str(phone_number)
    conv.state.phone_number_given_in_history = True

    # read back to the user
    if conv.language and conv.language.startswith("en-"):
        return {"utterance": f"Thanks. Just to confirm, that was {phone_number}?"}
    return f"You've collected the number: {phone_number}. To confirm you heard the user correctly, say the phone number back to them and ask if it's correct."
