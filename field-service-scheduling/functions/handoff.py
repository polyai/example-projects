from _gen import *  # <AUTO GENERATED>
from functions.utils import opening_hours_utterance

DEFAULT_DESTINATION = "CUSTOMER_CARE"

DEFAULT_HANDOFF_UTTERANCE = (
    "Please hold the line while I transfer you to a colleague who can help."
)

SKILL_IDS = {
    "INSIDE_SALES": "10000001",
    "CUSTOMER_CARE": "10000002",
    "ACCOUNT_CARE": "10000003",
    "NS_SCHEDULING_INBOUND": "10000004",
    "SPANISH": "10000005",
    "WELCOME_CALL": "10000006",
    "COMMERCIAL": "10000007",
    "BILLING": "10000008",
}


@func_description(
    "Call this function whenever you tell the user you are transferring them to actually complete the transfer"
)
@func_parameter(
    "handoff_reason",
    "The handoff code which represents the reason the user was handed off. It's provided in the transfer instructions. Copy it faithfully from the prompt.",
)
@func_parameter(
    "handoff_utterance",
    'This is to be said before handing off. If not provided, use "Please hold the line while I transfer you to a colleague who can help"',
)
@func_parameter(
    "handoff_destination",
    'This is the destination we\'ll hand off to. If not provided, feel free to use "CUSTOMER_CARE"',
)
def handoff(
    conv: Conversation,
    handoff_reason: str,
    handoff_utterance: str,
    handoff_destination: str,
):
    reason = (handoff_reason or "").strip().upper() or "UNSPECIFIED"
    destination = (handoff_destination or "").strip().upper() or DEFAULT_DESTINATION
    if destination not in SKILL_IDS:
        conv.log.warning(
            "Unknown handoff destination, using default",
            handoff_destination=destination,
            handoff_to=DEFAULT_DESTINATION,
        )
        destination = DEFAULT_DESTINATION
    utterance = handoff_utterance or DEFAULT_HANDOFF_UTTERANCE
    skill_id = SKILL_IDS[destination]

    conv.state.handoff_reason = reason
    conv.state.handoff_destination = destination
    conv.state.skill_id = skill_id
    conv.write_metric("HANDOFF_REASON", reason)
    conv.write_metric("HANDOFF_TO", destination)

    if conv.state.is_ooh:
        conv.write_metric("OUT_OF_HOURS_HANDOFF_REASON", reason)
        try:
            hours = opening_hours_utterance(
                conv.real_time_config.get("opening_hours", {})
            )
        except Exception as e:
            hours = None
            conv.log.warning("Could not build opening hours utterance", error=str(e))
        hours_part = f" {hours}" if hours else ""
        return {
            "utterance": f"Looks like we'll need a little extra help from our team here. Our office is currently closed.{hours_part} We appreciate your understanding and look forward to assisting you during regular business hours. Have a great rest of your day! Goodbye.",
            "hangup": True,
        }

    if conv.env in ("sandbox", "draft"):
        conv.log.info("Mock handoff", handoff_reason=reason, handoff_to=destination)
        return {"utterance": utterance, "hangup": True}

    if conv.state.incontact_id:
        # CXone accepts at most nine signal params (p1-p9)
        return {
            "utterance": utterance,
            "handoff": {
                "type": destination,
                "reason": reason,
                "cxone": {
                    "region": "na1",
                    "domain": "niceincontact",
                    "version": "v24.0",
                    "contactId": conv.state.incontact_id,
                    "signal": {
                        "params": {"p1": destination, "p2": skill_id, "p3": reason}
                    },
                },
            },
        }
    return conv.call_handoff(
        destination=destination, reason=reason, utterance=utterance
    )
