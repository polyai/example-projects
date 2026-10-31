from _gen import *  # <AUTO GENERATED>
from functions import idnv
from functions.handoff import handoff

TRANSFER_LINE = (
    "For cancellations I'll need to put you through to a colleague. One moment please."
)


def cancellation_enabled(conv) -> bool:
    """Cancelling in the agent is on unless real-time config turns it off."""
    settings = (conv.real_time_config or {}).get("settings", {})
    return bool(settings.get("cancel_order_flow_enabled", True))


@func_description("The caller wants to cancel an order.")
@func_parameter(
    "order_hint",
    "Anything the caller has said that picks out the order: an item ('the backpack'), or digits of the order number as they said them. Empty string if they haven't said.",
)
def start_cancel_order(conv: Conversation, order_hint: str):
    conv.state.order_hint = (order_hint or "").strip()
    conv.write_metric("PRIMARY_INTENT", "CANCEL_ORDER", write_once=True)
    if not cancellation_enabled(conv):
        return handoff(conv, "CANCEL_ORDER", TRANSFER_LINE, "CUSTOMER_SERVICE")
    gate = idnv.require(conv, "cancel_order")
    if gate:
        return gate
    conv.goto_flow("cancel_order")
