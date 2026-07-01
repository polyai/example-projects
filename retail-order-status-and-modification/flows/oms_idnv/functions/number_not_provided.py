from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call
from functions.utterances import utterance


@func_description("Use only if the user cannot or will not provide the order number.")
@func_parameter("times_called", "number of times this function has been called")
def number_not_provided(conv: Conversation, flow: Flow, times_called: int):
    if not conv.state.number_not_given:
        conv.state.number_not_given = True
        conv.say(utterance(conv, "idnv_order_hint"))
        flow.goto_step("Collect last 4")
    else:
        return transfer_call(
            conv,
            "DEFAULT",
            "CANNOT_LOOKUP_ORDER",
            utterance(conv, "transfer_one_second"),
        )
