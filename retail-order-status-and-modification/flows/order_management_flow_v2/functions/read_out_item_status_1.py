from _gen import *  # <AUTO GENERATED>


@func_description("Provide more information about item with the given shipping status.")
@func_parameter("status", "Item shipping status")
def read_out_item_status_1(conv: Conversation, flow: Flow, status: str):
    if not any(status == qty.shipping_status for qty in conv.state.item_to_look_at.consignments):
        return "The entry is the given status is not found. Please try again."

    item = conv.state.item_to_look_at
    conv.state.product_description = "The item is " + (
        f"{item.product_brand} {item.product_name} "
        f"(Size {item.product_size}, {item.product_color}) in "
        f"{item.product_category} category. "
        f"Quantity: {len([qty for qty in conv.state.item_to_look_at.consignments if status == qty.shipping_status])}. "
        f"Fulfillment Type: {item.fulfilment_type}. "
        f"Status: {status}"
    )

    if status == "PICKED_BY_CUST":
        flow.goto_step("Order picked up")
    elif status in ["CANCEL_INITIATED", "CANCELLED"]:
        if all(qty.cancel_reason in ["NLA", None] for qty in item.consignments):
            flow.goto_step("Item cancelled")
        else:
            flow.goto_step("Handoff")  # todo: return transfer_call instead
    elif status in ["CREATED", "SUBMITTED"]:
        flow.goto_step("Order not shipped yet")
    elif status in ["PICKED"]:
        flow.goto_step("Order not yet picked up")
    elif status == "SHIPPED":
        # CHECK: We assume all tracking url is the same here
        conv.state.tracking_url = next(
            (qty.tracking_url for qty in item.consignments if qty.tracking_url), ""
        )
        flow.goto_step("Order shipped")
