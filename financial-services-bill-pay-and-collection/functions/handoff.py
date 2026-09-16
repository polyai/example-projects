import re

from _gen import *  # <AUTO GENERATED>

HANDOFF_UTTERANCES = {
    "CARD_PAYMENT": "Sure, I'll transfer you to our payments team who can take your card details securely.",
    "SPEAK_TO": "Of course, let me connect you with one of our team members.",
    "COMPLAINT": "I'm sorry to hear that. Let me connect you with someone who can help resolve this.",
    "FRAUD": "I understand the urgency. Let me transfer you to our fraud team right away.",
    "DEFAULT": "Let me transfer you to someone who can help with that.",
}

DEFAULT_DESTINATION = "DEFAULT"

# first match wins, so payment keywords must stay ahead of card keywords
DESTINATION_RULES = [
    ("FRAUD", ("FRAUD", "PHISHING", "COMPROMISED")),
    ("VULNERABLE_CUSTOMER", ("THREAT_TO_LIFE", "VC_KEYWORD", "VC", "VULNERABLE")),
    ("COMPLAINTS", ("COMPLAINT",)),
    (
        "PAYMENTS",
        (
            "PAYMENT",
            "PAYEE",
            "BENEFICIARY",
            "STANDING_ORDER",
            "DIRECT_DEBIT",
            "BANK_TRANSFER",
            "MONEY_TRANSFER",
            "TRANSFER_BETWEEN_ACCOUNTS",
        ),
    ),
    ("CARDS", ("CARD", "PIN", "CONTACTLESS")),
]


def normalize_reason(reason) -> str:
    return str(reason or "").strip().upper()


def resolve_destination(reason) -> str:
    code = normalize_reason(reason)
    for destination, keywords in DESTINATION_RULES:
        for keyword in keywords:
            if re.search(rf"(?:^|_){keyword}S?(?:_|$)", code):
                return destination
    return DEFAULT_DESTINATION


@func_description(
    "Transfer the call to a live agent. Call this when the user needs help beyond what the virtual assistant can provide."
)
@func_parameter(
    "handoff_reason",
    "The reason for the transfer, e.g. CARD_PAYMENT, SPEAK_TO, COMPLAINT, FRAUD, or a short description.",
)
def handoff(conv: Conversation, handoff_reason: str):
    reason = normalize_reason(handoff_reason) or "OUT_OF_SCOPE"
    destination = resolve_destination(reason)
    utterance = (
        HANDOFF_UTTERANCES.get(reason)
        or HANDOFF_UTTERANCES.get(destination)
        or HANDOFF_UTTERANCES["DEFAULT"]
    )

    conv.state.handoff_reason = reason
    conv.state.handoff_to = destination
    conv.write_metric("HANDOFF_REASON", reason)
    conv.write_metric("HANDOFF_TO", destination)

    if conv.env in ("sandbox", "draft"):
        conv.log.info("Mock handoff", handoff_reason=reason, handoff_to=destination)
        return {"utterance": utterance, "hangup": True}

    return conv.call_handoff(
        destination=destination, reason=reason, utterance=utterance
    )
