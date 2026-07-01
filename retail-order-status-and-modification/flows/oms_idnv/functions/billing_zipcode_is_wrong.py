from _gen import *  # <AUTO GENERATED>
from functions.step_utils import is_ca_from_state
from functions.transfer_call import transfer_call
from functions.utterances import utterance


@func_description(
    "The billing zipcode/postal code is wrong. Call this function to determine the next step of the conversation."
)
def billing_zipcode_is_wrong(conv: Conversation, flow: Flow):
    if conv.state.denied_billing_zipcode_read_back:
        return transfer_call(
            conv,
            "DEFAULT",
            "IDNV_FAILED",
            utterance(conv, "idnv_transfer_default"),
        )
    else:
        conv.state.denied_billing_zipcode_read_back = True
        is_ca = is_ca_from_state(conv)
        if is_ca:
            flow.goto_step("Collect billing postcode")
            conv.say(utterance(conv, "idnv_wrong_postal_code"))
        else:
            flow.goto_step("Collect billing zipcode")
            conv.say(utterance(conv, "idnv_wrong_zipcode"))
