from _gen import *  # <AUTO GENERATED>
from functions import idnv, orders


def track_entry(conv: Conversation, flow: Flow):
    """Entry gate: unverified callers go to verify_caller and come back here."""
    conv.state.task = "track"
    gate = idnv.require(conv, "track_order")
    if gate:
        return gate

    conv.write_metric("ORDER_STATUS_FLOW_INITIATED", write_once=True)
    flow.goto_step("Track Order", "caller verified")
    hint, conv.state.order_hint = conv.state.order_hint or "", ""
    if hint:
        return (
            f"Call get_order_status now with order_hint='{hint}' (what the caller already said). "
            "Don't ask which order first.\n\n"
            + orders.call_state(
                conv, ["Task: track an order"], "Call get_order_status."
            )
        )
    return (
        "Call get_order_status now. Set order_hint to anything the caller has said that picks "
        "out an order (an item such as 'running shoes', or digits of the order number), or leave "
        "it empty. Don't ask which order first.\n\n"
        + orders.call_state(conv, ["Task: track an order"], "Call get_order_status.")
    )
