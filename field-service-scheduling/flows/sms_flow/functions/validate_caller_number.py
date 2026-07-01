import re

from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


def is_valid_US_number(phone_number: str):
    """
    Validates if a phone_number is a valid US number
    """
    if not phone_number:
        return False
    # Regex pattern to match US numbers
    pattern = r"^(?:\+1|1)?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$"

    is_match = re.match(pattern, phone_number)
    if is_match:
        return True
    return False


@func_description(
    "If the user has provided you with a valid US phone number, transition to read it back to them. If they decline to provide you with a number, or cannot remember their number, try again, then hand off."
)
@func_parameter(
    "sms_country_code",
    'The country code of the number the user has provided, without leading +. Assume US country code if not given: "1"',
)
@func_parameter(
    "sms_phone_number",
    'The most recent phone number the user has provided. Remove and ignore all punctuation. Ensure that multipliers such as "double" and "triple" are interpreted as the correct quantity of numbers. Must be 10 digits.',
)
@func_parameter(
    "declined_or_number_unknown",
    'Default to False. Set to True only if the user declines to offer their phone number - "no", "I don\'t want to give you my number" - or does not know their number - "I don\'t know it", "I don\'t have the phone number".',
)
def validate_caller_number(
    conv: Conversation,
    flow: Flow,
    sms_country_code: str,
    sms_phone_number: str,
    declined_or_number_unknown: bool,
):
    if declined_or_number_unknown:
        if conv.state.number_declined:
            return handoff(
                conv,
                "SMS_PHONE_NUMBER_NOT_PROVIDED",
                "I'm sorry, but I cannot continue without a phone number. Let me put you through to a team member, one moment please!",
                "CUSTOMER_CARE",
            )
        conv.state.number_declined = True
        return """Say: "I need a phone number to continue. Which number would you like me to send the link to?"
    """

    if not sms_country_code:
        sms_country_code = "1"

    conv.state.sms_phone_number = sms_phone_number.replace("-", "")
    conv.state.sms_country_code = sms_country_code
    conv.log.info("Got phone number", sms_phone_number=sms_phone_number)
    is_valid_number = is_valid_US_number("+" + sms_country_code + sms_phone_number)
    print(is_valid_number)

    if not is_valid_number:
        if conv.state.save_sms_number_retries < 1:
            conv.state.save_sms_number_retries += 1
            return """Say: "Could you try that number again for me please?"
      """
        if conv.state.save_sms_number_retries < 2:
            conv.state.save_sms_number_retries += 1
            return """Say: "I'm so sorry, could you try that one more time?"
      """
        return handoff(
            conv,
            "SMS_PHONE_NUMBER_COLLECTION_FAIL",
            "Sorry, but that still isn't working. Let me put you through to a team member, one moment please!",
            "CUSTOMER_CARE",
        )

    flow.goto_step("Readback SMS Number")
    return """To confirm that you have received the correct number, you must say: "Just to confirm, that's $sms_phone_number, correct?"
  """
