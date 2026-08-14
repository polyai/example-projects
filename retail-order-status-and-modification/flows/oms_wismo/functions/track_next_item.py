from _gen import *  # <AUTO GENERATED>
from flows.oms_wismo.functions.determine_order_status import determine_order_status


def _is_shipped(line) -> bool:
    consignments = getattr(line, "consignments", None) or []
    return bool(consignments) and all(
        getattr(c, "shipping_status", None) == "SHIPPED" for c in consignments
    )


@func_description("Track the user's next item")
def track_next_item(conv: Conversation, flow: Flow):
    if not getattr(conv.state, "looked_at", None):
        conv.state.looked_at = []

    all_lines = conv.state.order_details.order_lines
    remaining = [ol for ol in all_lines if ol not in conv.state.looked_at]

    if not remaining:
        conv.state.remaining_items = []
        return determine_order_status(conv, flow)

    # Prefer next item within the current shipment group (if any)
    active_group = getattr(conv.state, "picked_shipment_lines", None) or []
    next_in_group = next((ol for ol in active_group if ol in remaining), None)

    picked = next_in_group or remaining[0]

    if _is_shipped(picked):
        group_lines = [ol for ol in all_lines if _is_shipped(ol)]
    else:
        group_lines = [picked]

    conv.state.picked_shipment_lines = group_lines
    conv.state.picked_order = picked
    conv.state.looked_at.append(picked)
    conv.state.remaining_items = [
        ol for ol in all_lines if ol not in conv.state.looked_at
    ]

    return determine_order_status(conv, flow)
