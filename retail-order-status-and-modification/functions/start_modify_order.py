from _gen import *  # <AUTO GENERATED>
from functions.check_caller_number_orders import check_caller_number_orders


@func_description(
    "User wants to modify their order (change delivery address). Starts IDNV if not verified."
)
def start_modify_order(conv: Conversation):
    conv.state.idnv_started = True
    conv.state.order_action = "modify"
    conv.write_metric("MODIFY_ORDER_FLOW_INITIATED")
    return check_caller_number_orders(conv)
