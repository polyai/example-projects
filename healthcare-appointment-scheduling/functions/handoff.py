from _gen import *  # <AUTO GENERATED>
from functions import appointments
from functions.start_function import _is_ooh, local_now

HANDOFF_LOG_PREFIX = "[handoff]: "

DEFAULT_HANDOFF_UTTERANCE = (
    "Please hold the line while I transfer you to a colleague who can help. "
    "Putting you through now."
)

REASON_TO_TARGET = {
    "DEFAULT": "DEFAULT",
    "OUT_OF_SCOPE": "DEFAULT",
    "USER_INCOMPREHENSIBLE": "DEFAULT",
    "COMPLAINT": "DEFAULT",
    "QUALITY_CARE_CLERKS": "DEFAULT",
    "SMS_FAILURE": "DEFAULT",
    "SCHEDULING": "SCHEDULING",
    "NEW_PATIENT": "SCHEDULING",
    "ANNUAL_PHYSICAL": "SCHEDULING",
    "PREVENTATIVE_VACCINES": "SCHEDULING",
    "CLINICAL_SUPPORT": "CLINICAL_SUPPORT",
    "SYMPTOMS_CHECK": "CLINICAL_SUPPORT",
    "SAME_DAY_TRIAGE": "CLINICAL_SUPPORT",
    "SPEAK_TO": "CLINICAL_SUPPORT",
    "BILLING": "BILLING",
    "DENTAL_BILLING": "BILLING",
    "BILL_PAYMENT": "BILLING",
    "PAYMENT_PLAN": "BILLING",
    "SLIDING_FEE_DISCOUNT": "BILLING",
    "INSURANCE_CHECK": "BILLING",
    "RECORDS": "RECORDS",
    "LAB_RESULTS": "RECORDS",
    "HELP_WITH_FORMS": "RECORDS",
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


# Out of hours, every transfer is refused (the caller hears that we're closed and the
# call carries on) except these, which go through exactly as in hours:
# - emergencies and the clinical line (nurse, symptoms, same-day triage), which a caller
#   may need urgently whatever the time;
# - transfers the task tools make when they can't finish (ID&V failed, API error, no
#   slots, text failed, cancellations switched off): the tool has already said the
#   caller is being put through.
ALWAYS_TRANSFER_TARGETS = frozenset(
    {"EMERGENCY", "MEDICAL_EMERGENCY", "MENTAL_HEALTH_EMERGENCY", "CLINICAL_SUPPORT"}
)
TOOL_REASON_PREFIXES = ("IDNV_", "BOOKING_", "CANCEL", "RESCHEDUL", "SMS_")


def transfers_when_closed(reason: str) -> bool:
    return resolve_target(reason) in ALWAYS_TRANSFER_TARGETS or reason.startswith(
        TOOL_REASON_PREFIXES
    )


def closed_utterance(conv: Conversation) -> str:
    """We're closed, the hours (or the "not to hand" line when opening_hours is blank),
    and the after_hours_info attribute."""
    spoken = appointments.say_opening_hours(conv)
    hours = (
        f"Our opening hours are {spoken}."
        if appointments.hours_known(conv)
        else f"{spoken}."
    )
    variant = conv.variant
    after = (
        (getattr(variant, "after_hours_info", "") or "") if variant else ""
    ).strip()
    return (
        f"We're closed right now, so no one is available to take your call. {hours} "
        f"{after or 'Please call back when we are open.'} "
        "Is there anything else I can help with in the meantime?"
    )


def resolve_target(reason: str) -> str:
    if reason in REASON_TO_TARGET:
        return REASON_TO_TARGET[reason]
    for prefix, target in PREFIX_TO_TARGET:
        if reason.startswith(prefix):
            return target
    return "DEFAULT"


@func_description("[Agent Behaviour] Transfers the call to a live agent")
@func_parameter(
    "reason",
    "The handoff code which represents the reason the user was handed off. It's provided in the transfer instructions. Copy it faithfully from the prompt.",
)
@func_parameter(
    "utterance",
    "[OPTIONAL] This is to be said before handing off. If not provided, a default transfer message will be used.",
)
def handoff(conv: Conversation, reason: str, utterance: str):
    utterance = utterance or DEFAULT_HANDOFF_UTTERANCE
    reason = (reason or "DEFAULT").strip().upper() or "DEFAULT"

    conv.log.info(f"{HANDOFF_LOG_PREFIX}received handoff request", reason=reason)

    if not transfers_when_closed(reason) and _is_ooh(conv, local_now(conv)[1]):
        conv.log.info(
            f"{HANDOFF_LOG_PREFIX}closed, not transferring", handoff_reason=reason
        )
        return {"utterance": closed_utterance(conv)}

    handoff_to = resolve_target(reason)

    conv.state.handoff_reason = reason
    conv.state.handoff_to = handoff_to
    conv.write_metric("HANDOFF_REASON", reason)
    conv.write_metric("HANDOFF_TO", handoff_to)

    conv.log.info(
        f"{HANDOFF_LOG_PREFIX}resolved handoff destination",
        handoff_reason=reason,
        handoff_to=handoff_to,
    )

    if conv.env in ("sandbox", "draft"):
        conv.log.info("Mock handoff", handoff_reason=reason, handoff_to=handoff_to)
        return {"utterance": utterance, "hangup": True}
    return conv.call_handoff(destination=handoff_to, reason=reason, utterance=utterance)
