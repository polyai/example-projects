from _gen import *  # <AUTO GENERATED>
from functions.step_utils import is_ca_from_orders

from .utterances import utterance


@func_description(
    "Check whether the caller's phone number is associated with an order and route accordngly"
)
def check_caller_number_orders(conv: Conversation):
    conv.write_metric("IDNV_INITIATED", write_once=True)
    conv.state.in_idnv_flow = True
    conv.state.transfer_on_silence_loop = True

    orders = conv.state.orders_from_phone_number or []
    is_ca = is_ca_from_orders(conv, orders)
    postal_label = "postal code" if is_ca else "billing zipcode"
    step_name = "Collect billing postcode" if is_ca else "Collect billing zipcode"

    if orders:
        if len(orders) == 1:
            conv.state.singleton_order = True
            return {
                "utterance": utterance(
                    conv, "idnv_single_order", postal_label=postal_label
                ),
                "transition": {"goto_flow": "OMS_IDNV", "goto_step": step_name},
            }
        else:
            return {
                "utterance": utterance(conv, "idnv_multiple_orders"),
                "transition": {
                    "goto_flow": "OMS_IDNV",
                    "goto_step": "Check should collect phone number",
                },
            }
    else:
        return {
            "utterance": utterance(conv, "idnv_no_orders_ask_phone"),
            "transition": {
                "goto_flow": "OMS_IDNV",
                "goto_step": "Collect phone number",
            },
        }
