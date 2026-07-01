# from flows.oms_wismo.functions.determine_order_status import determine_order_status, _shipment_key
from _gen import *  # <AUTO GENERATED>
from flows.oms_wismo.functions.determine_order_status import (
    _status_bucket_key,
    determine_order_status,
)


@func_description(
    "Check which product the user means. Call this as many times as you need to, as appropriate. You may need to call it more than once over the course of the conversation."
)
@func_parameter("order_line_number", "The order line number ")
@func_parameter("times_called", "The number of times this function has been called.")
def validate_order_line(
    conv: Conversation, flow: Flow, order_line_number: str, times_called: float
):
    lines = conv.state.order_details.order_lines
    if order_line_number not in [str(order.order_line_number) for order in lines]:
        return "The order with the given number can't be found. Please try again."

    picked = next(order for order in lines if str(order.order_line_number) == order_line_number)
    # key = _shipment_key(picked)
    key = _status_bucket_key(picked)

    if key:
        # group_lines = [line for line in lines if _shipment_key(line) == key]
        group_lines = [line for line in lines if _status_bucket_key(line) == key]

        # remaining = [line for line in lines if _shipment_key(line) != key]
        remaining = [line for line in lines if _status_bucket_key(line) != key]
        # print(f"[validate_order_line] grouped: shipment_key={key}, group_size={len(group_lines)}, remaining={len(remaining)}")
        print(
            f"[validate_order_line] grouped: status_bucket_key={key}, group_size={len(group_lines)}, remaining={len(remaining)}"
        )

    else:
        group_lines = [picked]
        remaining = [line for line in lines if line is not picked]
        print(
            f"[validate_order_line] ungrouped: single line {picked.order_line_number}, remaining={len(remaining)}"
        )

    conv.state.picked_order = picked
    conv.state.remaining_items = remaining

    # conv.state.picked_shipment_key = key
    conv.state.picked_status_bucket_key = key
    conv.state.picked_shipment_lines = group_lines

    if not conv.state.looked_at:
        conv.state.looked_at = []
    conv.state.looked_at.append(picked)

    print(conv.state.remaining_items)
    print(conv.state.picked_order)
    print("len order lines = " + str(len(lines)))
    print(lines)

    return determine_order_status(conv, flow)
