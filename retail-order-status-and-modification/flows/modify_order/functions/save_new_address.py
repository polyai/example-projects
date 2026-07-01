from _gen import *  # <AUTO GENERATED>


@func_description("Save the new delivery address for the order being modified.")
@func_parameter("new_address", "the confirmed new delivery address")
def save_new_address(conv: Conversation, flow: Flow, new_address: str):
    order = conv.state.order_details
    if not order:
        conv.exit_flow()
        return {"content": "Order not found. Route through IDNV first."}

    order_number = order.order_number

    shipped_statuses = {"SHIPPED", "PICKED_BY_CUST", "DELIVERED"}
    has_shipped = any(
        c.shipping_status in shipped_statuses
        for line in order.order_lines
        for c in (line.consignments or [])
    )

    if has_shipped:
        conv.exit_flow()
        return {
            "content": (
                f"Order {order_number} has already shipped — the address can't be changed. "
                f"Let the customer know and offer to transfer to an agent."
            ),
        }

    conv.state.order_address_modified = True
    conv.state.new_delivery_address = new_address
    conv.write_metric("ORDER_ADDRESS_MODIFIED", order_number)
    conv.exit_flow()
    return {
        "content": (
            f"The delivery address for order {order_number} has been updated to: {new_address}. "
            f"Tell the customer: 'Done! I've updated the delivery address to {new_address}. "
            f"Is there anything else I can help with?'"
        ),
    }
