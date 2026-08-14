from _gen import *  # <AUTO GENERATED>
from functions.check_caller_number_orders import check_caller_number_orders


@func_description(
    "User wants to cancel their order. Starts IDNV if not verified, then cancels."
)
def cancel_order(conv: Conversation):
    conv.state.idnv_started = True
    conv.state.order_action = "cancel"
    conv.write_metric("CANCEL_ORDER_FLOW_INITIATED")
    return check_caller_number_orders(conv)
