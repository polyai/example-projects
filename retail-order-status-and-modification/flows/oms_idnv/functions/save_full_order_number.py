import requests
from _gen import *  # <AUTO GENERATED>
from flows.oms_idnv.functions.idnv_utils import ActionsIterator, get_bullet_points
from functions.oms_connector import get_order_details
from functions.step_utils import is_ca_from_order
from functions.transfer_call import transfer_call
from functions.utterances import utterance


@func_description("Save the provided full order number.")
def save_full_order_number(conv: Conversation, flow: Flow):
    try:
        order_found = get_order_details(conv, conv.state.full_order_number, timeout=10)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            order_found = None
        else:
            conv.log.error("Get orders by order number API error: %s", str(e))
            return transfer_call(
                conv,
                "DEFAULT",
                "ORDER_NOT_FOUND",
                utterance(conv, "idnv_transfer_default"),
            )
    except Exception as e:
        conv.log.error("Get orders by order number API error", e=str(e))
        conv.state.call_summary_additional_context = (
            "The agent attempted to transfer call due to an OMS API error."
        )
        return transfer_call(
            conv,
            "DEFAULT",
            "IDNV_FAILED",
            utterance(conv, "idnv_transfer_default"),
        )

    if not order_found:
        flow.goto_step("Collect full order number")
        conv.write_metric("ORDER_NOT_FOUND")
        return ActionsIterator(
            "ORDERS_NOT_FOUND_ACTION_2",
            [
                {"utterance": utterance(conv, "idnv_order_not_found")},
                {
                    "utterance": utterance(conv, "idnv_order_not_found_transfer"),
                    "content": get_bullet_points(
                        "If the user provides their order number again, immediately call the function order_number_provided.",
                        "If the user says 'yes', immediately call transfer_call with handoff_reason = 'IDNV_FAILED' and handoff_utterance = 'DEFAULT'",
                        "If the user says 'no' or 'no, thanks', immediately says: 'Can I have your order number again?'.",
                    ),
                },
            ],
        ).get_next(conv)

    conv.state.INVALID_FULL_ORDER_NUMBER_ACTIONS = None
    conv.state.ORDERS_NOT_FOUND_ACTION_2 = None
    conv.write_metric("ORDER_FOUND")
    conv.write_metric("ORDER_NUMBER", conv.state.full_order_number)
    conv.write_metric("ORDER_STATUS", order_found.order_status)
    conv.state.order_from_full_order_number = order_found
    is_ca = is_ca_from_order(conv, order_found)
    step_name = "Collect billing postcode" if is_ca else "Collect billing zipcode"
    flow.goto_step(step_name)
    return "Great, I can see an order with that number here. I just need to ask a couple security questions."
