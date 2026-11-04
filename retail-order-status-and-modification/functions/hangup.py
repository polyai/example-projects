from _gen import *  # <AUTO GENERATED>

GOODBYE = "Thanks for calling, and have a great day!"


@func_description("End the conversation, once the caller has nothing else.")
def hangup(conv: Conversation):
    conv.state.handoff_to = "CONTAINED"
    # A line that must be heard (the emergency line) is said again before the goodbye, so the
    # goodbye can't replace it when the call ends in the same turn.
    must_hear = str(conv.state.must_hear or "").strip()
    conv.state.must_hear = ""
    utterance = f"{must_hear} {GOODBYE}" if must_hear else GOODBYE
    return {"utterance": utterance, "hangup": True}
