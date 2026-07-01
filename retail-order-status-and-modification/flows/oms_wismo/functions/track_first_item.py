from _gen import *  # <AUTO GENERATED>
from flows.oms_wismo.functions.determine_order_status import (
    _status_bucket_key,
    determine_order_status,
)


@func_description("Track the first item in the user's order")
@func_parameter(
    "user_wants_all_items",
    "If the user said they wanted to hear the status for all / both of the items, True. Otherwise, False",
)
def track_first_item(conv: Conversation, flow: Flow, user_wants_all_items: bool):
    lines = conv.state.order_details.order_lines
    picked = next(iter(lines))
    key = _status_bucket_key(picked)

    if key == "SHIPPED":
        # Group ALL shipped lines together
        group_lines = [line for line in lines if _status_bucket_key(line) == "SHIPPED"]
        remaining = [line for line in lines if line not in group_lines]
    else:
        # Everything else: treat individually
        group_lines = [picked]
        remaining = [line for line in lines if line is not picked]

    conv.state.picked_order = picked
    conv.state.remaining_items = remaining
    conv.state.user_wants_all_items = user_wants_all_items

    conv.state.picked_shipment_key = key
    conv.state.picked_shipment_lines = group_lines

    if not conv.state.looked_at:
        conv.state.looked_at = []
    conv.state.looked_at.append(picked)

    return determine_order_status(conv, flow)
