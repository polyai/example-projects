from _gen import *  # <AUTO GENERATED>
from flows.order_management_flow_v2.functions.determine_order_status_1 import (
    determine_order_status_1,
)


@func_description("Track the user's next item")
def track_next_item_1(conv: Conversation, flow: Flow):
    conv.state.picked_order = next(
        order for order in (conv.state.remaining_items or [])
    )
    determine_order_status_1(conv, flow)
