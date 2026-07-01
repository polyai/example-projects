from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call
from functions.utterances import utterance


@func_description(
    "The phone number is wrong. Call this function to determine the next stage in the conversation."
)
def phone_number_is_wrong(conv: Conversation, flow: Flow):
    if conv.state.denied_phone_number_read_back:
        return transfer_call(
            conv,
            "DEFAULT",
            "IDNV_FAILED",
            utterance(conv, "idnv_transfer_default"),
        )
    else:
        conv.state.denied_phone_number_read_back = True
        flow.goto_step("Collect phone number")
        conv.say(utterance(conv, "idnv_wrong_phone_retry"))
        # return """Apologize to the user for mishearing the phone number.
        # - If the user already corrected their phone number (e.g., "No, it is 6505555500"), you MUST call {{ft:verify_phone_number}} with the new number in the next round. Do not ask again.
        # - Otherwise, ask the user to provide their phone number again.
        # """
        return "Apologise to the user for mishearding the phone number. Continue asking for user's phone number"
