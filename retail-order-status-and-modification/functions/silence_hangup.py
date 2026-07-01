from _gen import *  # <AUTO GENERATED>

from .utterances import utterance


@func_description(
    "[Agent Behaviour] Say goodbye and end the call if the user continues to be silent"
)
def silence_hangup(conv: Conversation):
    return {
        "utterance": utterance(conv, "silence_hangup"),
        "hangup": True,
    }
