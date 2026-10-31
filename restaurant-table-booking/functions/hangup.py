from _gen import *  # <AUTO GENERATED>


@func_description("End the call after saying goodbye.")
def hangup(conv: Conversation):
    conv.state.call_outcome = conv.state.call_outcome or "CONTAINED"
    return {"utterance": "Thanks for calling, goodbye!", "hangup": True}
