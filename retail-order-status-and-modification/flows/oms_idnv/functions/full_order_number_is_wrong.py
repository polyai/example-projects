from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call
from functions.utterances import utterance


@func_description(
    "The order number is wrong. Call this function to determine the next step of the conversation."
)
def full_order_number_is_wrong(conv: Conversation, flow: Flow):
    if conv.state.denied_full_order_number_read_back:
        return transfer_call(
            conv,
            "DEFAULT",
            "IDNV_FAILED",
            utterance(conv, "idnv_transfer_default"),
        )
    else:
        conv.state.denied_full_order_number_read_back = True
        flow.goto_step("Collect full order number")
        return """Apologize to the user for mishearing their order number.
        - If the user already corrected their order number (e.g., "No, it is U7314230965750992896"), you MUST call {{ft:verify_full_order_number}} with the new number in the next round. Do not ask again.
        - If the user says "no", or indicates that the order number they provided is incorrect, ask the user to provide their order number again."""
