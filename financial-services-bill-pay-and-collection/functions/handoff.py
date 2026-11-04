import re

from _gen import *  # <AUTO GENERATED>
from functions import hours

# Transfer lines held in code (design 2.1-2.8 and section 3): short, warm, and they say where
# the caller is going. A reason without its own line uses its destination's.
HANDOFF_UTTERANCES = {
    # Fraud and scams (2.6)
    "FRAUD": "I'm sorry to hear that. I'll put you through to our fraud team now. One moment, please.",
    "PHISHING_ATTEMPT": (
        "Thanks for checking. We'll never ask for your PIN or password. I'll put you through to "
        "our fraud team so they can look into it. One moment, please."
    ),
    "PAYMENT_SCAM": (
        "Thanks for telling me. Before you pay anything, I'd like to put you through to our "
        "fraud team to check this is genuine. One moment, please."
    ),
    "FREEZE_LOST_STOLEN_CARD": (
        "I'll put you through to our cards team so they can block it for you now. One moment, "
        "please."
    ),
    # Vulnerable customers and hardship (2.7)
    "THREAT_TO_LIFE": (
        "I'm really sorry you're going through this. If you're in danger right now, please hang "
        "up and call 911. I'm going to put you through to a colleague who can support you. One "
        "moment, please."
    ),
    "VC_KEYWORD_TRANSFER": (
        "Of course. I'll put you through to our support team now. One moment, please."
    ),
    "PAYMENT_PLAN": "Of course. I'll put you through to them now. One moment, please.",
    "BEREAVEMENT": (
        "I'm so sorry for your loss. I'll put you through to a colleague who can help with this. "
        "One moment, please."
    ),
    "FINANCIAL_ADVICE": "Of course. I'll put you through to our team now. One moment, please.",
    # Identity (2.1)
    "THIRD_PARTY": (
        "I'm afraid I can only go through an account with the account holder, but a colleague "
        "can help if you're authorized on it. I'll put you through now. One moment, please."
    ),
    # Payments (2.3)
    "CARD_PAYMENT": "Of course. I'll put you through to our payments team now. One moment, please.",
    "PAYMENT_OVER_PHONE_LIMIT": (
        "Of course. I'll put you through to our payments team now. One moment, please."
    ),
    "CARD_DISPUTES": (
        "Of course. I'll put you through to our disputes team now. One moment, please."
    ),
    # Team requests (2.8)
    "SPEAK_TO": "No problem. I'll put you through to the team now. One moment, please.",
    "COMPLAINT": (
        "I'm really sorry to hear that. I'll put you through to our complaints team so they can "
        "look into it. One moment, please."
    ),
    "OUT_OF_SCOPE": (
        "That's something our team can help with. I'll put you through now. One moment, please."
    ),
    # Destination defaults
    "PAYMENTS": "Of course. I'll put you through to our payments team now. One moment, please.",
    "CARDS": "Of course. I'll put you through to our cards team now. One moment, please.",
    "COMPLAINTS": (
        "I'm really sorry to hear that. I'll put you through to our complaints team so they can "
        "look into it. One moment, please."
    ),
    "VULNERABLE_CUSTOMER": (
        "Of course. I'll put you through to our support team now. One moment, please."
    ),
    "DEFAULT": "Of course. I'll put you through to the team now. One moment, please.",
}

DEFAULT_DESTINATION = "DEFAULT"

# first match wins, so payment keywords must stay ahead of card keywords
DESTINATION_RULES = [
    ("FRAUD", ("FRAUD", "PHISHING", "COMPROMISED", "SCAM")),
    ("VULNERABLE_CUSTOMER", ("THREAT_TO_LIFE", "VC_KEYWORD", "VC", "VULNERABLE")),
    ("COMPLAINTS", ("COMPLAINT",)),
    (
        "PAYMENTS",
        (
            "PAYMENT",
            "PAYEE",
            "BENEFICIARY",
            "AUTOPAY",
            "RECURRING_PAYMENT",
            "BANK_TRANSFER",
            "MONEY_TRANSFER",
            "TRANSFER_BETWEEN_ACCOUNTS",
        ),
    ),
    ("CARDS", ("CARD", "PIN", "CONTACTLESS")),
]

# Reasons that transfer even when the team is closed (design 2.6, 2.7 and 2.8).
ALWAYS_TRANSFER = ("THREAT_TO_LIFE",)


def normalize_reason(reason) -> str:
    return re.sub(r"[^A-Z0-9_]+", "_", str(reason or "").strip().upper()).strip("_")


def resolve_destination(reason) -> str:
    code = normalize_reason(reason)
    for destination, keywords in DESTINATION_RULES:
        for keyword in keywords:
            if re.search(rf"(?:^|_){keyword}S?(?:_|$)", code):
                return destination
    return DEFAULT_DESTINATION


def closed_line(conv) -> str:
    back = hours.back_line(conv)
    return (
        "Our team's closed right now, I'm afraid. "
        + (f"{back} " if back else "")
        + "Is there anything else I can help with in the meantime?"
    )


def transfer(conv: Conversation, reason: str, utterance: str = ""):
    """Transfer from inside a tool, with the tool's own line (or the reason's default).

    - A fraud transfer drops any payment in progress, so nothing is written after it.
    - A caller ID flagged as vulnerable sends every reason except fraud to the support team.
    - Out of hours (ooh_enabled, hours known): the closed line instead, except fraud (the
      24/7 fraud line first, then the transfer) and danger to life.
    """
    code = normalize_reason(reason) or "OUT_OF_SCOPE"
    destination = resolve_destination(code)
    line = (
        utterance
        or HANDOFF_UTTERANCES.get(code)
        or HANDOFF_UTTERANCES.get(destination)
        or HANDOFF_UTTERANCES["DEFAULT"]
    )
    if destination == "FRAUD":
        from functions import payments

        payments.clear(conv)
    elif conv.state.is_vulnerable_customer:
        destination = "VULNERABLE_CUSTOMER"

    if hours.has_hours(conv) and hours.is_out_of_hours(conv):
        if destination == "FRAUD":
            fraud_line = conv.state.fraud_line_spoken
            if fraud_line:
                line = f"Our fraud line is open 24 hours a day on {fraud_line}. {line}"
        elif code not in ALWAYS_TRANSFER:
            conv.write_metric("HANDOFF_CLOSED", code)
            return {"utterance": closed_line(conv)}

    conv.state.handoff_reason = code
    conv.state.handoff_to = destination
    conv.write_metric("HANDOFF_REASON", code)
    conv.write_metric("HANDOFF_TO", destination)

    if conv.env in ("sandbox", "draft"):
        conv.log.info("Mock handoff", handoff_reason=code, handoff_to=destination)
        return {"utterance": line, "hangup": True}

    return conv.call_handoff(destination=destination, reason=code, utterance=line)


@func_description(
    "Put the caller through to a colleague. Use the reason the topic, step or tool gives, e.g. SPEAK_TO, COMPLAINT, FRAUD, CARD_FRAUD, PAYMENT_SCAM, PHISHING_ATTEMPT, THREAT_TO_LIFE, VC_KEYWORD_TRANSFER, THIRD_PARTY, PAYMENT_PLAN, CARD_PAYMENT. It says the transfer line itself: don't say one before calling it."
)
@func_parameter(
    "handoff_reason", "The reason for the transfer, in capitals, e.g. SPEAK_TO."
)
def handoff(conv: Conversation, handoff_reason: str):
    return transfer(conv, handoff_reason)
