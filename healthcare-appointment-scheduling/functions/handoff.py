from _gen import *  # <AUTO GENERATED>
from functions import appointments
from functions.start_function import _is_ooh, local_now

HANDOFF_LOG_PREFIX = "[handoff]: "

DEFAULT_HANDOFF_UTTERANCE = (
    "No problem. I'll put you through to the team now. One moment, please."
)

# The safety lines (designs/healthcare.md 2.6). Spoken verbatim by this tool, whatever the
# model passes, so they can't be reworded, delayed or said twice.
SAFETY_LINES = {
    "MEDICAL_EMERGENCY": (
        "If this is an emergency, please hang up and call 911 now. If you can't, stay on the "
        "line and I'll put you through to our clinical team."
    ),
    "MENTAL_HEALTH_EMERGENCY": (
        "I'm really sorry you're feeling like this. You're not alone, and there are people who "
        "can help right now. If you're in immediate danger, please call 911, and you can call or "
        "text 988 at any time. I'm going to put you through to someone now, so please stay on "
        "the line."
    ),
    "EMERGENCY": (
        "If you're in danger, please hang up and call 911 now. If you can't, stay on the line "
        "and I'll put you through to our team."
    ),
}

# Transfer lines held in code: one warm sentence and "One moment, please."
REASON_LINES = {
    **SAFETY_LINES,
    "SAME_DAY_TRIAGE": "Of course. I'll put you through to our nurse now. One moment, please.",
    "SPEAK_TO": "Of course. I'll put you through to our nurse now. One moment, please.",
    "MEDICATION_QUESTION": "Of course. I'll put you through to our nurse now. One moment, please.",
    "LAB_RESULTS": (
        "Of course. I'll put you through to our clinical team now. One moment, please."
    ),
    "NEW_PATIENT": (
        "Welcome! Our scheduling team gets new patients set up. I'll put you through now. One "
        "moment, please."
    ),
    "COMPLAINT": (
        "I'm really sorry to hear that. I'll put you through to our team so they can help. One "
        "moment, please."
    ),
    "RUNNING_LATE": (
        "Thanks for letting us know. I'll put you through to the team so they can let your "
        "provider know. One moment, please."
    ),
    "SPEAK_TO_PROVIDER": (
        "Of course. I'll put you through to our team, who can get you to the right person. One "
        "moment, please."
    ),
    "SCHEDULING": (
        "Of course. I'll put you through to our scheduling team now. One moment, please."
    ),
    "BILLING": "Of course. I'll put you through to our billing team now. One moment, please.",
    "BILL_PAYMENT": "Of course. I'll put you through to our billing team now. One moment, please.",
    "INSURANCE_CHECK": (
        "Of course. I'll put you through to our billing team now. One moment, please."
    ),
    "SLIDING_FEE_DISCOUNT": (
        "Of course. I'll put you through to our billing team now. One moment, please."
    ),
    "RECORDS": (
        "Of course. I'll put you through to our medical records team now. One moment, please."
    ),
    "HELP_WITH_FORMS": (
        "Of course. I'll put you through to our medical records team now. One moment, please."
    ),
    "QUALITY_CARE_CLERKS": (
        "Of course. I'll put you through to our quality care team now. One moment, please."
    ),
    "PREVENTATIVE_VACCINES": (
        "Of course. I'll put you through to our immunization team now. One moment, please."
    ),
    "OUT_OF_SCOPE": "Of course. I'll put you through to the team now. One moment, please.",
    "DEFAULT": DEFAULT_HANDOFF_UTTERANCE,
}

REASON_TO_TARGET = {
    "DEFAULT": "DEFAULT",
    "OUT_OF_SCOPE": "DEFAULT",
    "USER_INCOMPREHENSIBLE": "DEFAULT",
    "COMPLAINT": "DEFAULT",
    "QUALITY_CARE_CLERKS": "DEFAULT",
    "LANGUAGE": "SCHEDULING",
    "SCHEDULING": "SCHEDULING",
    "SPEAK_TO_PROVIDER": "SCHEDULING",
    "RUNNING_LATE": "SCHEDULING",
    "NEW_PATIENT": "SCHEDULING",
    "PREVENTATIVE_VACCINES": "SCHEDULING",
    "APPOINTMENT_NOT_PICKED": "SCHEDULING",
    "CLINICAL_SUPPORT": "CLINICAL_SUPPORT",
    "SYMPTOMS_CHECK": "CLINICAL_SUPPORT",
    "SAME_DAY_TRIAGE": "CLINICAL_SUPPORT",
    "SPEAK_TO": "CLINICAL_SUPPORT",
    "MEDICATION_QUESTION": "CLINICAL_SUPPORT",
    "LAB_RESULTS": "CLINICAL_SUPPORT",
    "SILENCE_AFTER_SPEECH": "CLINICAL_SUPPORT",
    "BILLING": "BILLING",
    "BILL_PAYMENT": "BILLING",
    "PAYMENT_PLAN": "BILLING",
    "SLIDING_FEE_DISCOUNT": "BILLING",
    "INSURANCE_CHECK": "BILLING",
    "RECORDS": "RECORDS",
    "HELP_WITH_FORMS": "RECORDS",
    "SMS_FAILURE": "DEFAULT",
    "SMS_NUMBER_NOT_CAPTURED": "DEFAULT",
    "EMERGENCY": "EMERGENCY",
    "MEDICAL_EMERGENCY": "MEDICAL_EMERGENCY",
    "MENTAL_HEALTH_EMERGENCY": "MENTAL_HEALTH_EMERGENCY",
}

PREFIX_TO_TARGET = (
    ("IDNV_", "SCHEDULING"),
    ("BOOKING_", "SCHEDULING"),
    ("CANCEL", "SCHEDULING"),
    ("RESCHEDUL", "SCHEDULING"),
)

# Out of hours, every transfer is refused except to these: emergencies and the clinical
# line, which a caller may need whatever the time.
ALWAYS_TRANSFER_TARGETS = frozenset(
    {"EMERGENCY", "MEDICAL_EMERGENCY", "MENTAL_HEALTH_EMERGENCY", "CLINICAL_SUPPORT"}
)
# Transfers the tools make when they can't finish (ID&V failed, an EHR error, cancellations
# switched off, a text that failed). Out of hours they say when the team is back instead.
TOOL_REASON_PREFIXES = (
    "IDNV_",
    "BOOKING_",
    "CANCEL",
    "RESCHEDUL",
    "SMS_",
    "APPOINTMENT_",
)


def transfers_when_closed(reason: str) -> bool:
    return resolve_target(reason) in ALWAYS_TRANSFER_TARGETS


def resolve_target(reason: str) -> str:
    if reason in REASON_TO_TARGET:
        return REASON_TO_TARGET[reason]
    for prefix, target in PREFIX_TO_TARGET:
        if reason.startswith(prefix):
            return target
    return "DEFAULT"


def closed_utterance(conv: Conversation) -> str:
    """We're closed, when we're next open, and the after_hours_info attribute. Only used
    when the hours are known: blank hours are never closed."""
    when, opens = appointments.next_open(conv, local_now(conv)[1])
    variant = conv.variant
    after = (
        (getattr(variant, "after_hours_info", "") or "") if variant else ""
    ).strip()
    return " ".join(
        part
        for part in (
            "We're closed right now, I'm afraid, so I can't put you through.",
            f"We're open again {when} from {appointments.say_time(opens)}.",
            after,
            appointments.ANYTHING_ELSE,
        )
        if part
    )


def tool_closed_utterance(conv: Conversation, reason: str) -> str:
    """Out of hours, a tool that can't finish says when the team can help instead."""
    when, opens = appointments.next_open(conv, local_now(conv)[1])
    back = f"from {appointments.say_time(opens)} {when.removeprefix('on ')}"
    if reason == "IDNV_DECLINED":
        return (
            "No problem. We're closed right now, but the team can help confirm your details "
            f"{back}."
        )
    if reason.startswith("IDNV_") and reason != "IDNV_API_ERROR":
        return (
            "I'm sorry, I wasn't able to confirm your details. We're closed right now, but the "
            f"team can help {back}."
        )
    return f"I'm sorry, I couldn't do that just now. We're closed right now, but the team can help {back}."


@func_description("[Agent Behaviour] Transfers the call to a live agent")
@func_parameter(
    "reason",
    "The handoff code the instructions give, copied exactly, e.g. 'SAME_DAY_TRIAGE'.",
)
@func_parameter(
    "utterance",
    "What to say before the transfer, only where the instructions give one. The tool says the line for most reasons.",
)
def handoff(conv: Conversation, reason: str, utterance: str):
    reason = (reason or "DEFAULT").strip().upper() or "DEFAULT"
    utterance = REASON_LINES.get(reason) or utterance or DEFAULT_HANDOFF_UTTERANCE

    conv.log.info(f"{HANDOFF_LOG_PREFIX}received handoff request", reason=reason)
    if reason in SAFETY_LINES:
        # A line that must be heard: goodbye_and_hangup says it again if it ends the call.
        conv.state.must_hear = utterance

    if not transfers_when_closed(reason) and _is_ooh(conv, local_now(conv)[1]):
        conv.log.info(
            f"{HANDOFF_LOG_PREFIX}closed, not transferring", handoff_reason=reason
        )
        conv.write_metric("HANDOFF_REFUSED_CLOSED", reason)
        if reason.startswith(TOOL_REASON_PREFIXES):
            return {"utterance": tool_closed_utterance(conv, reason)}
        return {"utterance": closed_utterance(conv)}

    handoff_to = resolve_target(reason)
    conv.state.handoff_reason = reason
    conv.state.handoff_to = handoff_to
    conv.log.info(
        f"{HANDOFF_LOG_PREFIX}resolved handoff destination",
        handoff_reason=reason,
        handoff_to=handoff_to,
    )

    if conv.env in ("sandbox", "draft"):
        conv.log.info("Mock handoff", handoff_reason=reason, handoff_to=handoff_to)
        conv.write_metric("HANDOFF_REASON", reason)
        conv.write_metric("HANDOFF_TO", handoff_to)
        return {"utterance": utterance, "hangup": True}
    return conv.call_handoff(destination=handoff_to, reason=reason, utterance=utterance)
