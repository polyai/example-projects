from _gen import *  # <AUTO GENERATED>
from functions.is_ooh import is_ooh
from functions.transfer_call import transfer_call

from .create_call_summary import get_call_summary_prompt
from .utterances import utterance as get_utterance


@func_description("Pre-handoff logic")
@func_parameter(
    "has_user_agreed",
    "bool variable denoting whether user has explicitly agreed to a handoff or not",
)
@func_parameter(
    "handoff_reason",
    'The metric explaining why the call was transferred. The string has to be exactly as instructed. If no information about reason is available, set it to "DEFAULT".',
)
@func_parameter("utterance", "Utterance to use in handoff, if none, set it to None")
def pre_handoff(
    conv: Conversation, has_user_agreed: bool, handoff_reason: str, utterance: str
):
    conv.state.handoff_reason = handoff_reason

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
        return {"content": get_call_summary_prompt(conv)}

    return transfer_call(
        conv,
        "DEFAULT",
        conv.state.handoff_reason,
        get_utterance(conv, "transfer_short"),
    )
