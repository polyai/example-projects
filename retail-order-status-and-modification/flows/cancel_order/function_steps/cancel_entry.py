from _gen import *  # <AUTO GENERATED>
from flows.cancel_order.functions.process_cancel_order import cancel_reply
from functions import idnv, orders


def cancel_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the order to cancel (none, one or several)."""
    conv.state.task = "cancel"
    gate = idnv.require(conv, "cancel_order")
    if gate:
        return gate

    conv.write_metric("CANCEL_ORDER_FLOW_INITIATED", write_once=True)
    flow.goto_step("Cancel Order", "caller verified")
    hint, conv.state.order_hint = conv.state.order_hint or "", ""
    order, _matches, orders_ = orders.pick_order(conv, hint)
    if order:
        return cancel_reply(conv, order)
    if not orders_:
        return "There are no recent orders on this account to cancel. Tell the caller and ask if there's anything else."
    return (
        "If the caller has already said which order (an item, or digits of the order number), "
        "call process_cancel_order with that as order_hint and caller_confirmed='false'. "
        + orders.which_order_instruction(orders_, conv, "process_cancel_order")
    )
