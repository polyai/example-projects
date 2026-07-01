from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call
from functions.utterances import utterance


@func_description("Check whether the number you read back to the user is correct.")
@func_parameter(
    "readback_number_correct",
    'Set to False by default. Set to True only if the user explicitly confirms that the number you have read back to them is correct: "yes".',
)
@func_parameter(
    "phone_number_provided",
    "Default to False. Set to True only if the user has already provided a new phone number to use.",
)
def check_read_back_is_correct(
    conv: Conversation, flow: Flow, readback_number_correct: bool, phone_number_provided: bool
):
    if conv.state.readback_occurred and not readback_number_correct:
        return transfer_call(
            conv,
            "SMS_PHONE_NUMBER_COLLECTION_FAIL",
            utterance(conv, "transfer_short"),
        )

    if not readback_number_correct:
        conv.state.readback_occurred = True
        if phone_number_provided:
            flow.goto_step("Phone number collected")
            return """The user has already provided a number. Do not say anything, and immediately call validate_phone_number
        """
        flow.goto_step("Phone number collected")
        return """Ask the user to provide the correct phone number to send the SMS to: "Please could you tell me the correct number?".
      """

    flow.goto_step("Send SMS")
    return
