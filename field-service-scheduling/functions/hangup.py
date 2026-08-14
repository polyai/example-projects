from _gen import *  # <AUTO GENERATED>


@func_description("End the conversation")
def hangup(conv: Conversation):
    conv.state.handoff_to = "CONTAINED"
    return {
        "utterance": "Okay, then! Have a great rest of your day! Goodbye.",
        "hangup": True,
    }
