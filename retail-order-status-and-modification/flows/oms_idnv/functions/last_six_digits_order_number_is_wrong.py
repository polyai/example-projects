from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call
from functions.utterances import utterance


@func_description(
    "The last six digits of the order number is wrong. Call this function to determine the next step of the conversation."
)
def last_six_digits_order_number_is_wrong(conv: Conversation, flow: Flow):
    if conv.state.denied_last_six_digits_read_back:
        return transfer_call(
            conv,
            "DEFAULT",
            "IDNV_FAILED",
            utterance(conv, "idnv_transfer_default"),
        )
    else:
        conv.state.denied_last_six_digits_read_back = True
        flow.goto_step("Collect last 4")
        conv.say(utterance(conv, "idnv_wrong_last6_retry"))
        # return "Apologise to the user for mishearding the order number."
        # return """- If the user already corrected their order number (e.g., "No, it is 123456"), you MUST call order_number_provided with the new number in the next round. Do not ask again.
        # - Otherwise, ask the user to provide the last six digits of their order number again.
        # Without mentioning the provided order number again, apologise to the user for mishearing their order number.
        # """
