from _gen import *  # <AUTO GENERATED>
from functions.utils import opening_hours_utterance


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
    conv: Conversation, handoff_reason: str, handoff_utterance: str, handoff_destination: str
):
    conv.state.handoff_reason = handoff_reason.upper()
    conv.state.handoff_destination = handoff_destination.upper()
    route_mapping = {
        "INSIDE_SALES": "10000001",
        "CUSTOMER_CARE": "10000002",
        "ACCOUNT_CARE": "10000003",
        "NS_SCHEDULING_INBOUND": "10000004",
        "SPANISH": "10000005",
        "WELCOME_CALL": "10000006",
        "COMMERCIAL": "10000007",
        "BILLING": "10000008",
    }
    regional_mapping = {}

    skill_id = route_mapping.get(conv.state.handoff_destination, "10000002")
    if skill_id == "10000003" and conv.real_time_config.get("regional_routing"):
        skill_id = regional_mapping.get(conv.state.dnis, {}).get("act", "10000003")
    elif skill_id == "10000002" and conv.real_time_config.get("regional_routing"):
        skill_id = regional_mapping.get(conv.state.dnis, {}).get("care", "10000002")

    conv.state.skill_id = skill_id

    if conv.state.is_ooh:
        conv.write_metric("OUT_OF_HOURS_HANDOFF_REASON", handoff_reason)
        try:
            hours = opening_hours_utterance(conv.real_time_config.get("opening_hours", {}))
        except Exception:
            hours = None
            conv.log.error("error parsing opening hours", exc_info=True)
        hours_part = f" {hours}" if hours else ""
        return {
            "utterance": f"Looks like we'll need a little extra help from our team here. Our office is currently closed.{hours_part} We appreciate your understanding and look forward to assisting you during regular business hours. Have a great rest of your day! Goodbye.",
            "hangup": True,
        }

    # Build signal parameters: p1=handoff_destination, p2=skill_id, p3=handoff_reason
    # Maximum of 9 parameters (p1 to p9) can be passed according to CXone API
    signal_params = {
        "p1": handoff_destination.upper(),
        "p2": skill_id,
        "p3": handoff_reason.upper(),
    }

    return {
        "utterance": handoff_utterance,
        "handoff": {
            "type": handoff_destination.upper(),
            "reason": handoff_reason.upper(),
            "cxone": {
                "region": "na1",
                "domain": "niceincontact",
                "version": "v24.0",
                "contactId": conv.state.incontact_id,
                "signal": {"params": signal_params},
            },
        },
    }
