from _gen import *  # <AUTO GENERATED>
from functions.check_caller_number_orders import check_caller_number_orders


@func_description("Collect user's order details and track their order")
def track_order(conv: Conversation):
    conv.state.idnv_started = True
    conv.state.order_action = "track"
    conv.write_metric("ORDER_STATUS_FLOW_INITIATED")
    return check_caller_number_orders(conv)
