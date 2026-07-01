from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call
from functions.utterances import utterance


@func_description(
    "Use only if the user cannot or will not provide a phone number or an order number."
)
def number_unknown(conv: Conversation, flow: Flow):
    if conv.state.entered_phone_number_validation:
        return transfer_call(
            conv,
            "DEFAULT",
            "IDNV_FAILED",
            utterance(conv, "transfer_short"),
        )
    else:
        flow.goto_step("Collect full order number")
