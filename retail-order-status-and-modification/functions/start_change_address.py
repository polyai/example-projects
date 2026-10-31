from _gen import *  # <AUTO GENERATED>
from functions import idnv


@func_description("The caller wants to change the delivery address on an order.")
@func_parameter(
    "order_hint",
    "Anything the caller has said that picks out the order: an item ('the backpack'), or digits of the order number as they said them. Empty string if they haven't said.",
)
def start_change_address(conv: Conversation, order_hint: str):
    conv.state.order_hint = (order_hint or "").strip()
    conv.write_metric("PRIMARY_INTENT", "CHANGE_ADDRESS", write_once=True)
    gate = idnv.require(conv, "change_address")
    if gate:
        return gate
    conv.goto_flow("change_address")
