from _gen import *  # <AUTO GENERATED>


@func_description("Start modifying the delivery address for the current order.")
def process_modify_order(conv: Conversation, flow: Flow):
    order = conv.state.order_details
    if not order:
        return {
            "content": "No order loaded. The customer needs to go through verification first."
        }

    shipped_statuses = {"SHIPPED", "PICKED_BY_CUST", "DELIVERED"}
    has_shipped = any(
        c.shipping_status in shipped_statuses
        for line in order.order_lines
        for c in (line.consignments or [])
    )

    if has_shipped:
        conv.state.order_action = None
        return {
            "content": (
                "This order has already shipped — the delivery address can no longer be changed. "
                "Let the customer know and offer to transfer to an agent if they need help."
            ),
        }

    conv.state.modify_order_number = order.order_number
    conv.state.order_action = None
    conv.goto_flow("modify_order")
