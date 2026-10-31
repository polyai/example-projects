from _gen import *  # <AUTO GENERATED>
from functions import idnv


@func_description(
    "The caller wants to know where an order is, when it will arrive or ship, or what's happened to it (including missing parcels and tracking that isn't updating). Call it as soon as that's clear, even if they're also giving details. A bare yes or yeah to the greeting's 'track an order?' question, or 'it's about my order' with no other task named, means this: call it."
)
@func_parameter(
    "order_hint",
    "Anything the caller has said that picks out the order: an item ('the backpack'), or digits of the order number as they said them. Empty string if they haven't said.",
)
def start_track_order(conv: Conversation, order_hint: str):
    conv.state.order_hint = (order_hint or "").strip()
    conv.write_metric("PRIMARY_INTENT", "TRACK_ORDER", write_once=True)
    gate = idnv.require(conv, "track_order")
    if gate:
        return gate
    conv.goto_flow("track_order")
