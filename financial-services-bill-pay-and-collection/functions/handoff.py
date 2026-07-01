from _gen import *  # <AUTO GENERATED>

HANDOFF_UTTERANCES = {
    "CARD_PAYMENT": "Sure, I'll transfer you to our payments team who can take your card details securely.",
    "SPEAK_TO": "Of course, let me connect you with one of our team members.",
    "COMPLAINT": "I'm sorry to hear that. Let me connect you with someone who can help resolve this.",
    "FRAUD": "I understand the urgency. Let me transfer you to our fraud team right away.",
    "DEFAULT": "Let me transfer you to someone who can help with that.",
}


@func_description(
    "Transfer the call to a live agent. Call this when the user needs help beyond what the virtual assistant can provide."
)
@func_parameter(
    "handoff_reason",
    "The reason for the transfer, e.g. CARD_PAYMENT, SPEAK_TO, COMPLAINT, FRAUD, or a short description.",
)
def handoff(conv: Conversation, handoff_reason: str):
    reason = handoff_reason.upper()
    utterance = HANDOFF_UTTERANCES.get(reason, HANDOFF_UTTERANCES["DEFAULT"])

    conv.state.handoff_reason = reason
    conv.write_metric("HANDOFF_REASON", reason)

    if conv.env in ("sandbox", "draft"):
        conv.log.info("Mock handoff", reason=reason)
        return {"utterance": utterance, "hangup": True}

    return conv.call_handoff(destination="default", reason=reason, utterance=utterance)
