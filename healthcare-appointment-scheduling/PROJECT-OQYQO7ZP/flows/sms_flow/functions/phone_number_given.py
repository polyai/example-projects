import plog
from _gen import *  # <AUTO GENERATED>
from functions.start_sms_flow import offer_handoff_after_sms_failed


@func_description("Save the phone number to which the user wants to receive the SMS")
@func_parameter(
    "phone_number", "The phone number provided by the user (excluding the country code)"
)
@func_parameter("country_code", 'Country code, without leading "+". Default to 0 if not provided.')
def phone_number_given(conv: Conversation, flow: Flow, phone_number: int, country_code: int):
    log_prefix = "[phone_number_given]: "
    plog.info(
        f"{log_prefix} phone_number='{phone_number}', country_code='{country_code}'", is_pii=True
    )
    # regional constants
    min_digits = 10 if conv.language == "en-US" else 9
    max_digits = 10 if conv.language == "en-US" else 10
    default_country_code = 1

    if not country_code:
        country_code = default_country_code

    if conv.state.sms_number_retried:
        return offer_handoff_after_sms_failed(conv)  # retry limit exceeded
    conv.state.sms_number_retried = True

    # length validation
    if len(str(phone_number)) < min_digits:
        if conv.language in ["en-US", "en-GB"]:
            return {
                "utterance": "Sorry, I didn't quite catch the full number. Could you say that number again?"
            }
        return "Ask the user to say that number again."
    if len(str(phone_number)) > max_digits:
        if conv.language in ["en-US", "en-GB"]:
            return {
                "utterance": "Just so I'm sure, could you repeat that number one more time please?"
            }
        return "Ask the user to say that number again."

    conv.state.sms_phone_number = "+" + str(country_code) + str(phone_number)
    conv.state.phone_number_given_in_history = True

    # read back to the user
    if conv.language and conv.language.startswith("en-"):
        return {"utterance": f"Thanks. Just to confirm, that was {phone_number}?"}
    return f"You've collected the number: {phone_number}. To confirm you heard the user correctly, say the phone number back to them and ask if it's correct."
