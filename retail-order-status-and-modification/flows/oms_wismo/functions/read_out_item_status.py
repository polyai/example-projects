from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call


@func_description("Provide more information about item with the given shipping status.")
@func_parameter("status", "Item shipping status")
def read_out_item_status(conv: Conversation, flow: Flow, status: str):
    if not any(
        status == qty.shipping_status for qty in conv.state.item_to_look_at.consignments
    ):
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

    conv.state.item_fulfilment_type = (
        "shipping" if item.fulfilment_type == "SHIP" else "pick up"
    )

    if status == "PICKED_BY_CUST":
        return {
            "content": conv.state.pickedup_content,
            "transition": {
                "goto_flow": "OMS_WISMO",
                "goto_step": "Determine what user needs next",
            },
        }
    elif status in ["CANCEL_INITIATED", "CANCELLED"]:
        if all(qty.cancel_reason in ["NLA", None] for qty in item.consignments):
            return {
                "content": conv.state.cancelled_NLA_content,
                "transition": {
                    "goto_flow": "OMS_WISMO",
                    "goto_step": "Determine what user needs next",
                },
            }
        else:
            conv.state.call_summary_additional_context = "The agent attempted to transfer call because the order has status 'CANCELLED_BY_STORE_NOT_NLA'."
            return transfer_call(
                conv,
                "DEFAULT",
                "CANCELLED_BY_STORE_NOT_NLA",
                "Ah, I've found your order but I think you'll need to speak to someone else about it. One sec while I put you through.",
            )

    elif status in ["CREATED", "SUBMITTED"]:
        if conv.state.item_fulfilment_type == "shipping":
            return {
                "content": conv.state.submitted_shipping_content,
                "transition": {
                    "goto_flow": "OMS_WISMO",
                    "goto_step": "Determine what user needs next",
                },
            }
        elif conv.state.item_fulfilment_type == "pick up":
            return {
                "content": conv.state.submitted_pickup_content,
                "transition": {
                    "goto_flow": "OMS_WISMO",
                    "goto_step": "Determine what user needs next",
                },
            }
    elif status == "PICKED":
        return {
            "content": conv.state.pickup_ready_content,
            "transition": {
                "goto_flow": "OMS_WISMO",
                "goto_step": "Determine what user needs next",
            },
        }
    elif status == "PICKED_BY_CUST":
        return {
            "content": conv.state.pickedup_content,
            "transition": {
                "goto_flow": "OMS_WISMO",
                "goto_step": "Determine what user needs next",
            },
        }
    elif status == "SHIPPED":
        # CHECK: We assume all tracking url is the same here
        conv.state.tracking_url = next(
            (qty.tracking_url for qty in item.consignments if qty.tracking_url), ""
        )
        return {
            "content": conv.state.shipped_content,
            "transition": {
                "goto_flow": "OMS_WISMO",
                "goto_step": "Offer NARVAR tracking link",
            },
        }
