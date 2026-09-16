from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call


@func_description("Function used when we exceed the retry limit for a step")
@func_parameter("destination", "Destination to transfer to")
@func_parameter("reason", "Reason for the transfer")
@func_parameter("utterance", "Utterance to say before transferring")
def step_fallback_transfer(
    conv: Conversation, destination: str, reason: str, utterance: str
):
    return transfer_call(
        conv,
        destination or "DEFAULT",
        reason or "RETRY_LIMIT_EXCEEDED",
        utterance
        or "Ok. I'll put you through to someone who can help with this. One moment.",
    )
