from _gen import *  # <AUTO GENERATED>


@func_description("transfers the call to a live agent")
def transfer_call_no_arg(conv: Conversation):
    if conv.state.cannot_handoff:
        conv.state.cannot_handoff = False
        return {
            "utterance": "I'm afraid the restaurant is currently closed - please call back when we're open. Is there anything else I can help you with?"
        }
    return """
        Call "try_transfer_call" with the appropriate 'handoff_reason' argument and
        "handoff_utterance" = "I'll put you through to someone who can help with that. One second." and "handoff_to" = "default"
    """
