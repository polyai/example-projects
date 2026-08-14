from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff
from functions.try_send_sms import try_send_sms


@func_description(
    "If the user states that the number you have read back to them is correct, proceed to send the SMS. If they state that it is not, attempt to collect it one more time. If you have unsuccessfully attempted to collect the user's number twice, handoff."
)
@func_parameter(
    "readback_number_correct",
    'Set to False by default. Set to True only if the user explicitly confirms that the number you have read back to them is correct: "yes".',
)
@func_parameter(
    "phone_number_provided",
    "Default to False. Set to True only if the user has already provided a new phone number to use.",
)
def save_caller_number_or_collect_again(
    conv: Conversation,
    flow: Flow,
    readback_number_correct: bool,
    phone_number_provided: bool,
):
    if conv.state.readback_occurred and not readback_number_correct:
        return handoff(
            conv,
            "SMS_PHONE_NUMBER_COLLECTION_FAIL",
            "Ok, let me put you through to a team member, one moment please!",
            "CUSTOMER_CARE",
        )

    if not readback_number_correct:
        conv.state.readback_occurred = True
        if phone_number_provided:
            flow.goto_step("Collect SMS Number")
            return """The user has already provided a number. Do not say anything, and immediately call validate_caller_number
        """
        flow.goto_step("Collect SMS Number")
        return """Ask the user to provide the correct phone number to send the SMS to: "Please could you tell me the correct number?".
      """

    return try_send_sms(conv)
