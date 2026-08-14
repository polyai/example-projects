from _gen import *  # <AUTO GENERATED>
from flows.oms_idnv.functions.idnv_utils import ActionsIterator, get_bullet_points
from functions.oms_connector import get_orders_by_phone_number
from functions.step_utils import is_ca_from_orders
from functions.transfer_call import transfer_call
from functions.utterances import utterance


@func_description("Save provided phone number.")
def save_phone_number(conv: Conversation, flow: Flow):
    try:
        orders_found = get_orders_by_phone_number(
            conv, conv.state.phone_number, timeout=10
        )
    except Exception as e:
        conv.log.error("Get orders by phone number API error", e=str(e))
        conv.state.call_summary_additional_context = (
            "The agent attempted to transfer call due to an OMS API error."
        )
        return transfer_call(
            conv,
            "DEFAULT",
            "IDNV_FAILED",
            utterance(conv, "idnv_transfer_default"),
        )

    if not orders_found:
        flow.goto_step("Collect phone number")
        return ActionsIterator(
            "ORDERS_NOT_FOUND_ACTION",
            [
                {
                    "utterance": utterance(conv, "idnv_orders_not_found"),
                    "content": get_bullet_points(
                        "If the user provides their phone number-even if it's same number as before-immediately call the function phone_number_provided.",
                        "Otherwise, keep asking for the user's phone number.",
                    ),
                },
                {
                    "utterance": utterance(conv, "idnv_orders_not_found_transfer"),
                    "content": get_bullet_points(
                        "If the user provides their phone number again, immediately call the function phone_number_provided.",
                        "If the user says 'yes', immediately call transfer_call with handoff_reason = 'IDNV_FAILED'",
                        "If the user says 'no' or 'no, thanks', immediately says: 'Can I have your phone number again?'.",
                    ),
                },
            ],
        ).get_next(conv)

    # Reset Counter before entering next step
    conv.state.INVALID_PHONE_NUMBER_ACTIONS = None
    conv.state.ORDERS_NOT_FOUND_ACTION = None
    conv.write_metric("IDNV_PHONE_NUMBER_FOUND")
    conv.state.orders_from_phone_number = orders_found
    is_ca = is_ca_from_orders(conv, orders_found)
    postal_label = "postal code" if is_ca else "zipcode"
    step_name = "Collect billing postcode" if is_ca else "Collect billing zipcode"
    conv.say(utterance(conv, "idnv_order_found_multi_zip", postal_label=postal_label))
    flow.goto_step(step_name)
