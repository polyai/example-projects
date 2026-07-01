from _gen import *  # <AUTO GENERATED>

from .utterances import utterance


@func_description(
    "Play a goodbye message and end the conversation. Do this if and only if the user doesn't have any more questions."
)
def end_call(conv: Conversation):
    conv.state.call_outcome = "hangup"

    return {
        "utterance": utterance(conv, "goodbye"),
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
