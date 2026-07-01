from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call
from functions.utterances import utterance


@func_description(
    "Follow-up to the transfer_utterance response control keywords. After preventing the LLM from saying a transfer utterance, return a prompt to call the transfer_call function instead."
)
def attempt_transfer_call(conv: Conversation):
    return transfer_call(
        conv,
        destination="DEFAULT",
        reason="SPEAK_TO",
        utterance=utterance(conv, "transfer_default"),
    )
