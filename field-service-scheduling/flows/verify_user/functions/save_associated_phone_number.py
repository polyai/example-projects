from _gen import *  # <AUTO GENERATED>
import re

from functions.handoff import handoff
from functions.routes_api_call import DispatchApiError, get_customer_details


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


digit_to_word = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}


def number_string_to_words(number_str: str):
    return ", ".join(digit_to_word[d] for d in number_str)


@func_description(
    "Once you have asked, you must always attempt save the phone number the user provides you with. Handoff if the user declines to provide their phone number, or says that they don't know it."
)
@func_parameter(
    "country_code",
    'The country code of the number the user has provided, without leading +. Assume US country code if not given: "1"',
)
@func_parameter(
    "phone_number",
    'The most recent phone number the user has provided. Remove and ignore all punctuation. Ensure that multipliers such as "double" and "triple" are interpreted as the correct quantity of numbers. Must be 10 digits.',
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=2,
    delay_responses=[
        ("One second, I'm just looking that up", 3),
        ("one more moment please", 3),
    ],
)
def save_associated_phone_number(
    conv: Conversation, flow: Flow, country_code: str, phone_number: str
):
    if not conv.state.save_phone_number_retries:
        conv.state.save_phone_number_retries = 0

    if not country_code:
        country_code = "1"

    conv.state.phone_number = phone_number.replace("-", "")
    conv.state.country_code = country_code
    conv.log.info("Got phone number", phone_number=phone_number)
    conv.write_metric("ASR_PHONE_NUMBER_COLLECTED", None)
    if "+" in phone_number:
        is_valid_number = is_valid_US_number(phone_number)
    else:
        is_valid_number = is_valid_US_number("+" + country_code + phone_number)

    if not is_valid_number:
        if conv.state.save_phone_number_retries < 1:
            conv.state.save_phone_number_retries += 1
            return """Say: "Could you try that number again for me please?"
      """
        if conv.state.save_phone_number_retries < 2:
            conv.state.save_phone_number_retries += 1
            return """Say: "I'm so sorry, could you try that one more time?"
      """
        return handoff(
            conv,
            "PHONE_NUMBER_COLLECTION_FAIL",
            "Ok, let me put you through to a team member, one moment please!",
            "CUSTOMER_CARE",
        )

    try:
        customer_details = get_customer_details(conv)
        conv.state.customer_details_list = customer_details
    except DispatchApiError:
        return handoff(
            conv,
            "API_FAIL",
            "Ok, let me put you through to a team member, one moment please!",
            "CUSTOMER_CARE",
        )

    if not customer_details:
        if conv.state.save_phone_number_retries < 1:
            conv.state.save_phone_number_retries += 1
            flow.goto_step("Readback number")
            conv.state.phone_number_spelled_out = number_string_to_words(phone_number)
            return """The user has provided a number that doesn't match any accounts - you should now read the number back to them just to check that you heard them right.
      """
        if conv.state.save_phone_number_retries < 2:
            conv.state.save_phone_number_retries += 1
            return """Say: "I still can't find your account, is there another number I should check?"
      """
        return handoff(
            conv,
            "PHONE_NUMBER_LOOKUP_FAIL",
            "Ok, let me put you through to a team member, one moment please!",
            "CUSTOMER_CARE",
        )

    flow.goto_step("Collect zip code")
    return """You found an account, now you need to make sure it's the right one by asking for their zip code.
  """
