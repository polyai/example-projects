from collections import Counter

from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call


@func_description(
    "Determine what the status of the order is, and so what the next stage of the conversation should be."
)
def determine_order_status_1(conv: Conversation, flow: Flow):
    conv.write_metric("ORDER_STATUS_FLOW_INITIATED")
    conv.state.order_status_flow_initiated = True
    conv.state.order_status = conv.state.order_details.order_status

    if (
        conv.state.picked_order is None
        and len(conv.state.order_details.order_lines) > 1
        and len(
            {
                (consignment.shipping_status, order.fulfilment_type)
                for order in conv.state.order_details.order_lines
                for consignment in order.consignments
            }
        )
        > 1
    ):
        order_items_listing = ""
        for item in conv.state.order_details.order_lines:
            order_items_listing += f"- {item.line_description(include_status=False)}.\n"
        conv.state.order_items_listing = order_items_listing
        flow.goto_step("Decide which item to look at")
        return

    # caller has picked an item, or there's only one item, or all item share the same shipping_status and fullfillment type

    item = conv.state.picked_order or conv.state.order_details.order_lines[0]
    conv.state.item_fulfilment_type = (
        "shipping" if item["fulfilment_type"] == "SHIP" else "pick up"
    )

    if conv.state.picked_order or len(conv.state.order_details.order_lines) == 1:
        conv.state.product_description = (
            f"The item is {item.line_description(include_line_number=False)}"
        )
    else:
        description = "The items are as follow:\n"
        for item in conv.state.order_details.order_lines:
            description += f"- {item.line_description(include_line_number=False)}\n"
        conv.state.product_description = description

    if conv.state.order_status == "FRAUD_CHECK_FAILED":
        print(">>>>>001")
        return transfer_call(
            conv,
            "DEFAULT",
            "FRAUD_CHECK_FAILED",
            "Ah, I've found your order but I think you'll need to speak to someone else about it. One sec while I put you through.",
        )
    # flow.goto_step("Handoff")

    elif conv.state.order_status == "CANCELLED":
        if item.consignments and all(
            qty.cancel_reason == "NLA" for qty in item.consignments
        ):
            # NLA = item no longer available
            print(">>>>>002")
            flow.goto_step("Item cancelled")
        else:
            # flow.goto_step("Handoff")
            print(">>>>>003")
            return transfer_call(
                conv,
                "DEFAULT",
                "CANCELLED_BY_STORE_NOT_NLA",
                "Ah, I've found your order but I think you'll need to speak to someone else about it. One sec while I put you through.",
            )
    elif conv.state.order_status in [
        "SUBMITTED",
        "WAIT_FRAUD_SYSTEM_CHECK",
        "FRAUD_CHECKED",
    ]:
        print(">>>>>004")
        flow.goto_step("Order not shipped yet")

    elif conv.state.order_status == "FULFILMENT_PROCESSING":
        # At this point, either there's one item with same/different shipping_status along quantity line
        # or there's multiple item with same shipping_status accross all their quantity lines
        if cancelled_item := next(
            (
                qty
                for qty in item.consignments
                if qty.shipping_status in ["CANCEL_INITIATED", "CANCELLED"]
            ),
            None,
        ):
            if cancelled_item.cancel_reason == "NLA":
                print(">>>>>1")
                flow.goto_step("Item cancelled")
            else:
                # flow.goto_step("Handoff")
                print(">>>>>2")
                return transfer_call(
                    conv,
                    "DEFAULT",
                    "CANCELLED_BY_STORE_NOT_NLA",
                    "Ah, I see your order but I think you'll need to speak to someone else about it. One sec while I put you through.",
                )
        elif all(
            qty.shipping_status in ["CREATED", "SUBMITTED"] for qty in item.consignments
        ):
            print(">>>>>3")
            flow.goto_step("Order not shipped yet")
        elif all(qty.shipping_status == "SHIPPED" for qty in item.consignments):
            print(">>>>>4")
            conv.state.tracking_url = next(
                qty.tracking_url for qty in item.consignments
            )  # CHECK: assume all tracking url is the same here
            flow.goto_step("Order shipped")
        elif all(qty.shipping_status == "PICKED" for qty in item.consignments):
            print(">>>>>5")
            flow.goto_step("Order not yet picked up")
        else:
            # CHECK THIS
            print(">>>>>6")
            setup_order_entries_disambiguation_step(conv, item)
            flow.goto_step("Decide which item entry to look at")
    elif conv.state.order_status == "FULFILMENT_COMPLETE":
        shipping_statuses = {qty.shipping_status for qty in item.consignments}
        if shipping_statuses == {"PICKED_BY_CUST"}:
            print(">>>>>A")
            flow.goto_step("Order picked up")
        elif shipping_statuses.issubset(["CANCELLED", "PICKED_BY_CUST"]):
            if all(qty.cancel_reason in ["NLA", None] for qty in item.consignments):
                print(">>>>>B")
                flow.goto_step("Item cancelled")
            else:
                # flow.goto_step("Handoff")
                print(">>>>>C")
                return transfer_call(
                    conv,
                    "DEFAULT",
                    "CANCELLED_BY_STORE_NOT_NLA",
                    "Ah, I see your order but I think you'll need to speak to someone else about it. One sec while I put you through.",
                )
        elif shipping_statuses.issubset(["SHIPPED"]):
            print(">>>>>D")
            # CHECK: We assume all tracking url is the same here
            conv.state.tracking_url = next(
                (qty.tracking_url for qty in item.consignments if qty.tracking_url), ""
            )
            flow.goto_step("Order shipped")
        elif shipping_statuses.issubset(["PICKED_BY_CUST"]):
            print(">>>>>E")
            # CHECK: We assume all tracking url is the same here
            conv.state.tracking_url = next(
                (qty.tracking_url for qty in item.consignments if qty.tracking_url), ""
            )
            flow.goto_step("Order picked up")
        else:
            print(">>>>>F")
            # Some item are shipped, and some are cancelled, determine the next step
            setup_order_entries_disambiguation_step(conv, item)
            flow.goto_step("Decide which item entry to look at")


def setup_order_entries_disambiguation_step(conv: Conversation, item):
    conv.state.item_description = (
        f"{item.product_brand} {item.product_name} "
        f"(Size {item.product_size}, {item.product_color}) in "
        f"{item.product_category} category. "
        f"Fulfillment Type: {item.fulfilment_type}. "
    )

    status_counter = Counter(
        f"{consignment.shipping_status}" for consignment in item.consignments
    )

    item_entries_description = ""
    for status, count in status_counter.items():
        item_entries_description += f"- Status: {status}; Quantity: {count}\n"
    conv.state.item_entries_description = item_entries_description
    conv.state.item_to_look_at = item
