from _gen import *  # <AUTO GENERATED>
from functions import orders


@func_description("The caller wants to change the delivery address on an order.")
@func_parameter(
    "order_hint",
    "Any item the caller has named, even in passing ('my shoes' gives 'shoes', 'the backpack' gives 'backpack'), or digits of the order number as they said them. Empty string if they haven't named one: call this straight away anyway, never ask for the item first.",
)
def start_change_address(conv: Conversation, order_hint: str):
    conv.state.order_hint = (order_hint or "").strip()
    conv.write_metric("PRIMARY_INTENT", "CHANGE_ADDRESS", write_once=True)
    gate = orders.require(conv, "change_address")
    if gate:
        return gate
    conv.goto_flow("change_address")
