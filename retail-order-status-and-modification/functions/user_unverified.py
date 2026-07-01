from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call
from functions.utterances import utterance

from .zendesk_client import update_custom_fields_on_ticket


@func_description(
    "If user doesn't know their loyalty number, or has given an incorrect number three times, update zendesk ticket as 'unverified'."
)
def user_unverified(conv: Conversation):
    conv.write_metric("LOYALTY_NUMBER_UNVERIFIED")
    first_name = conv.state.zendesk_first_name
    last_name = conv.state.zendesk_last_name
    conv.state.verified = False
    conv.log.info(
        "Updating Zendesk ticket for unverified user",
        first_name=first_name,
        last_name=last_name,
        ticket_id=conv.state.zendesk_ticket_id,
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
        utterance(conv, "transfer_straight_through"),
    )
