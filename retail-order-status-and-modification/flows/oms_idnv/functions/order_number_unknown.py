from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call
from functions.utterances import utterance


@func_description("Use only if the user cannot or will not provide an order number.")
def order_number_unknown(conv: Conversation, flow: Flow):
    if not conv.state.full_order_number_not_given:
        conv.state.full_order_number_not_given = True
        conv.say(utterance(conv, "idnv_order_hint"))
        flow.goto_step("Collect full order number")
    return transfer_call(conv, "DEFAULT", "IDNV_FAILED", utterance(conv, "transfer_one_second"))
