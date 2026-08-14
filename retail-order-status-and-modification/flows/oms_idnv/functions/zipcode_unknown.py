from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call
from functions.utterances import utterance


@func_description(
    "Use only if the user cannot or will not provide a billing zipcode or postal code."
)
def zipcode_unknown(conv: Conversation, flow: Flow):
    return transfer_call(
        conv, "DEFAULT", "IDNV_FAILED", utterance(conv, "transfer_one_second")
    )
