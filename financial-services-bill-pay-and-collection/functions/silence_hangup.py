from _gen import *  # <AUTO GENERATED>

SILENCE_LINE = (
    "I'm sorry, I still can't hear you, so I'll end the call now. Please call back whenever "
    "you're ready. Goodbye."
)


@func_description(
    "[Agent Behaviour] Say goodbye and end the call if the caller stays silent to the end"
)
def silence_hangup(conv: Conversation):
    conv.write_metric("SILENCE_HANGUP")
    return {"utterance": SILENCE_LINE, "hangup": True}
