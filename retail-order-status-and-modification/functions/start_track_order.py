from _gen import *  # <AUTO GENERATED>
from functions import idnv, orders


@func_description(
    "The caller wants to know where an order is, when it will arrive or ship, or what's happened to it (late, delivered but not received, missing items, tracking not updating). Call it as soon as that's clear, even if they're also giving details. A yes to the greeting's 'Are you looking to check on an order?' means this: call it."
)
@func_parameter(
    "order_hint",
    "Any item the caller has named, even in passing ('my shoes' gives 'shoes', 'the backpack' gives 'backpack'), or digits of the order number as they said them. Empty string if they haven't named one: call this straight away anyway, never ask for the item first.",
)
@func_parameter(
    "try_other_account",
    "'true' only when no orders were found on the account and the caller wants to try a different phone number. Otherwise 'false'.",
)
def start_track_order(conv: Conversation, order_hint: str, try_other_account: str):
    conv.state.order_hint = (order_hint or "").strip()
    conv.write_metric("PRIMARY_INTENT", "TRACK_ORDER", write_once=True)
    if str(try_other_account).strip().lower() == "true" and not orders.caller_orders(
        conv
    ):
        # Back to verification with the new number: forget the account with no orders.
        conv.state.idnv = None
        idnv.state(conv)
        conv.state.selected_order_number = ""
    gate = orders.require(conv, "track_order")
    if gate:
        return gate
    conv.goto_flow("track_order")
