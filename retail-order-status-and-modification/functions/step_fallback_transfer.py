from _gen import *  # <AUTO GENERATED>


@func_description("Function used when we exceed the retry limit for a step")
@func_parameter("destination", "Destination to transfer to")
@func_parameter("reason", "Reason for the transfer")
@func_parameter("utterance", "Utterance to say before transferring")
def step_fallback_transfer(conv: Conversation, destination: str, reason: str, utterance: str):
    """
    Function used when we exceed the retry limit for a step.

    Args:
        conv: Conversation object containing state and context
        destination: Destination to transfer to (default: "DEFAULT")
        reason: Reason for the transfer (default: "RETRY_LIMIT_EXCEEDED")
        utterance: Utterance to say before transferring (default: "Ok. I'll put you through to someone who can help with this. One moment.")

    Returns:
        The result of the handoff call
    """
    if destination is None:
        destination = "DEFAULT"
    if reason is None:
        reason = "RETRY_LIMIT_EXCEEDED"
    if utterance is None:
        utterance = "Ok. I'll put you through to someone who can help with this. One moment."

    return conv.call_handoff(destination=destination, reason=reason, utterance=utterance)
