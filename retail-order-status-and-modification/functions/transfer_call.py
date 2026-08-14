from _gen import *  # <AUTO GENERATED>
from functions.is_ooh import (
    is_ooh,
)  # refactored this out so can be shared with pre-handoff

from .create_call_summary import get_call_summary_prompt
from .utterances import utterance as get_utterance

# from datetime import datetime
# from zoneinfo import ZoneInfo


# def is_ooh():
#   # return False
#   est_current_time = datetime.now(ZoneInfo("America/Chicago")).time()
#   opening_time = datetime.strptime("06:00", "%H:%M").time()
#   closing_time = datetime.strptime("23:59", "%H:%M").time()
#   return not (opening_time < est_current_time < closing_time)


@func_description("Transfer the user to a different department")
@func_parameter(
    "destination",
    "The destination where the call should be transferred, which is DEFAULT. It should only EVER be DEFAULT.",
)
@func_parameter(
    "reason",
    'The metric explaining why the call was transferred. The string has to be exactly as instructed. If the user asked to speak to an agent, the reason should be SPEAK_TO. If no information about reason is available, set it to "DEFAULT". ',
)
@func_parameter(
    "utterance",
    'The message that will be played to the user upon transferring the call. If no message provided, set this to "DEFAULT".',
)
def transfer_call(conv: Conversation, destination: str, reason: str, utterance: str):
    # validate arguments and set defaults
    if not utterance or utterance.upper() == "DEFAULT":
        utterance = get_utterance(conv, "transfer_default")
    if not destination:
        destination = "DEFAULT"
    if not reason:
        reason = "DEFAULT"

    # if conv.state.in_idnv_flow:
    #   reason = "IDNV_FAILED"

    conv.state.call_outcome = "handoff"

    # out of hours handling
    if is_ooh(conv):
        conv.state.action_after_call_summary = {
            "utterance": conv.state.ooh_utterance,
            "handoff": {
                "bye": {
                    "sip_headers": {
                        "X-Route-Destination": "",
                        "X-Route-Reason": "",
                        "X-Zendesk-Ticket": str(conv.state.zendesk_ticket_id) or "",
                    }
                }
            },
        }
    else:
        conv.state.action_after_call_summary = {
            "utterance": utterance,
            "handoff": {
                "type": destination.upper(),
                "reason": reason.upper(),
                "bye": {
                    "sip_headers": {
                        "X-Route-Destination": "Voice",
                        "X-Route-Reason": reason.upper() or "",
                        "X-Zendesk-Ticket": str(conv.state.zendesk_ticket_id) or "",
                    }
                },
            },
        }
    return {"content": get_call_summary_prompt(conv)}
