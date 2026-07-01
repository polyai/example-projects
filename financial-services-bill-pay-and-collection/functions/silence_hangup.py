from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Agent Behaviour] Say goodbye and end the call if the user continues to be silent"
)
def silence_hangup(conv: Conversation):
    conv.write_metric("SILENCE_HANGUP")
    return {
        "utterance": "I'm really sorry, but I still can't hear you. I'm going to hang up now, but please feel free to call back when you're ready. Thanks for calling, have a great rest of your day, goodbye!",
        "hangup": True,
    }
