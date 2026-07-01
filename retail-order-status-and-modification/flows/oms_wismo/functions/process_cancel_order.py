from _gen import *  # <AUTO GENERATED>


@func_description("Process the cancellation of the current order.")
@func_parameter("reason", "the reason the customer wants to cancel")
def process_cancel_order(conv: Conversation, flow: Flow, reason: str):
    order = conv.state.order_details
    if not order:
        return {"content": "No order loaded. The customer needs to go through verification first."}

    order_number = order.order_number

    shipped_statuses = {"SHIPPED", "PICKED_BY_CUST", "DELIVERED"}
    has_shipped = any(
        c.shipping_status in shipped_statuses
        for line in order.order_lines
        for c in (line.consignments or [])
    )

    if has_shipped:
        return {
            "content": (
                f"Order {order_number} has already shipped and cannot be cancelled. "
                f"Tell the customer: 'I'm sorry, this order has already shipped so I'm unable to cancel it. "
                f"You can return it once it arrives, or I can transfer you to an agent who can help.'"
            ),
        }

    conv.state.order_cancelled = True
    conv.state.order_action = None
    conv.write_metric("ORDER_CANCELLED", order_number)
    conv.exit_flow()
    return {
        "content": (
            f"Order {order_number} has been cancelled. Reason: {reason}. "
            f"Tell the customer: 'Your order has been cancelled. "
            f"You should receive a confirmation email shortly. Is there anything else I can help with?'"
        ),
    }
