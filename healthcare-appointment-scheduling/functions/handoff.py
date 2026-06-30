from _gen import *  # <AUTO GENERATED>

HANDOFF_LOG_PREFIX = "[handoff]: "

DEFAULT_HANDOFF_UTTERANCE = (
    "Please hold the line while I transfer you to a colleague who can help. "
    "Putting you through now."
)

# Maps handoff reasons from LLM to handoff target names defined in handoffs.yaml.
# Reasons not listed here fall through to "DEFAULT".
REASON_TO_TARGET = {
    "DEFAULT": "DEFAULT",
    "SCHEDULING": "SCHEDULING",
    "CLINICAL_SUPPORT": "CLINICAL_SUPPORT",
    "SYMPTOMS_CHECK": "CLINICAL_SUPPORT",
    "SPEAK_TO": "CLINICAL_SUPPORT",
    "BILLING": "BILLING",
    "RECORDS": "RECORDS",
    "EMERGENCY": "EMERGENCY",
    "MEDICAL_EMERGENCY": "MEDICAL_EMERGENCY",
    "MENTAL_HEALTH_EMERGENCY": "MENTAL_HEALTH_EMERGENCY",
    "OUT_OF_SCOPE": "DEFAULT",
    "USER_INCOMPREHENSIBLE": "DEFAULT",
}


@func_description("[Agent Behaviour] Transfers the call to a live agent")
@func_parameter(
    "reason",
    "The handoff code which represents the reason the user was handed off. "
    "It's provided in the transfer instructions. Copy it faithfully from the prompt.",
)
@func_parameter(
    "utterance",
    "[OPTIONAL] This is to be said before handing off. If not provided, a default "
    "transfer message will be used.",
)
def handoff(conv: Conversation, reason: str, utterance: str):
    utterance = utterance or DEFAULT_HANDOFF_UTTERANCE
    reason = reason.strip().upper()

    conv.log.info(f"{HANDOFF_LOG_PREFIX}received handoff request", reason=reason)

    # Resolve handoff target from reason
    handoff_to = REASON_TO_TARGET.get(reason, "DEFAULT")

    # Write metrics
    conv.state.handoff_reason = reason
    conv.state.handoff_to = handoff_to
    conv.write_metric("HANDOFF_REASON", reason)
    conv.write_metric("HANDOFF_TO", handoff_to)

    conv.log.info(
        f"{HANDOFF_LOG_PREFIX}resolved handoff destination",
        handoff_reason=reason,
        handoff_to=handoff_to,
    )

    return conv.call_handoff(handoff_to, reason, utterance)
