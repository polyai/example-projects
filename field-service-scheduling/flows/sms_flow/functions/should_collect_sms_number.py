from _gen import *  # <AUTO GENERATED>
from functions.try_send_sms import try_send_sms


@func_description(
    "If the user states that we can send the SMS to the number they are calling from, transition to send the SMS. If the user states that we cannot, transition to collect their number. If the user at any point explicitly provides a phone number to send the SMS to, transition to validate their number."
)
@func_parameter(
    "phone_number_provided",
    "Default to False. Set to True only if the user has provided a phone number to use. Set to False if the user states that the number they are calling from is the one to send the SMS to.",
)
@func_parameter(
    "should_collect_number",
    'Default to False. Set to True only if the user says "no", or does not want to send the SMS to the number they are calling from.',
)
def should_collect_sms_number(
    conv: Conversation,
    flow: Flow,
    phone_number_provided: bool,
    should_collect_number: bool,
):
    if not should_collect_number:
        conv.state.sms_phone_number = conv.state.phone_number
        conv.state.sms_country_code = "1"
        return try_send_sms(conv)

    if phone_number_provided:
        flow.goto_step("Collect SMS Number")
        return """The user has already provided a number. Do not say anything, and immediately call validate_caller_number
    """

    flow.goto_step("Collect SMS Number")
    return """Ask the user to provide a phone number to send the SMS to: "Please could you tell me the number you want to send the SMS to?".
  """
