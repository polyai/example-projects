from _gen import *  # <AUTO GENERATED>
from functions.is_ooh import is_ooh
from functions.transfer_call import transfer_call

from .create_call_summary import get_call_summary_prompt
from .utterances import utterance as get_utterance
from .zendesk_client import update_custom_fields_on_ticket


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
def pre_handoff(conv: Conversation, has_user_agreed: bool, handoff_reason: str, utterance: str):
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
    else:
        if conv.state.idnv_started:
            return transfer_call(
                conv,
                "DEFAULT",
                conv.state.handoff_reason,
                get_utterance(conv, "transfer_short"),
            )

        if conv.state.verified is not False:
            if not conv.state.order_details:
                orders = conv.state.orders_from_phone_number or []

                # IF TESTING!
                if conv.state.testing_loyalty_id:
                    conv.state.order_details = orders[1] if orders else None
                else:
                    conv.state.order_details = orders[0] if orders else None

                # conv.state.order_details = orders[0] if orders else None
                print(conv.state.order_details)

            order_details = conv.state.order_details
            loyalty_id = getattr(order_details, "loyalty_id", None)
            if loyalty_id:
                conv.write_metric("LOYALTY_FLOW_INITIATED")
                if has_user_agreed:
                    return {
                        "utterance": get_utterance(conv, "loyalty_ask_agreed"),
                        "transition": {
                            "goto_flow": "LOYALTY_IDNV",
                        },
                    }
                elif not has_user_agreed:
                    return {
                        "utterance": get_utterance(conv, "loyalty_ask_not_agreed"),
                        "transition": {
                            "goto_flow": "LOYALTY_IDNV",
                        },
                    }
        first_name = conv.state.zendesk_first_name
        last_name = conv.state.zendesk_last_name
        conv.state.verified = False
        conv.log.info(
            "Updating Zendesk ticket for unverified user",
            first_name=first_name or "Not found",
            last_name=last_name or "Not found",
            ticket_id=conv.state.zendesk_ticket_id or "Not found",
        )
        update_custom_fields_on_ticket(
            conv,
            first_name=first_name,
            last_name=last_name,
        )

        return transfer_call(
            conv,
            "DEFAULT",
            conv.state.handoff_reason,
            get_utterance(conv, "transfer_short"),
        )
