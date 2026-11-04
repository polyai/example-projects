from _gen import *  # <AUTO GENERATED>
from flows.cancel_order.functions.process_cancel_order import TOOL, WHICH, cancel_reply
from functions import orders


def cancel_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the order to cancel (none, one or several)."""
    conv.state.task = "cancel"
    gate = orders.require(conv, "cancel_order")
    if gate:
        return gate

    conv.write_metric("CANCEL_ORDER_FLOW_INITIATED", write_once=True)
    flow.goto_step("Cancel Order", "caller verified")
    hint, conv.state.order_hint = conv.state.order_hint or "", ""
    order, matches, orders_ = orders.pick_order(conv, hint)
    if order:
        return cancel_reply(conv, order)
    if not orders_:
        return (
            "Say: \"I can't see any recent orders on your account. Is it possible you ordered with "
            'a different phone number, or as a guest?"'
        )
    if hint and orders.names_an_order(hint) and not matches:
        return orders.no_matching_order(orders_, conv, TOOL, hint)
    return (
        "If the caller has already said which order, call process_cancel_order with that as "
        "order_hint and caller_confirmed='false'. Otherwise: "
        + orders.which_order_instruction(
            orders_, conv, TOOL, WHICH, matched=matches if hint and matches else None
        )
    )
