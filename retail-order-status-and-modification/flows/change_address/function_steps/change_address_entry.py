from _gen import *  # <AUTO GENERATED>
from flows.change_address.functions.save_new_address import TOOL, WHICH, address_reply
from functions import orders


def change_address_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the order to re-address (none, one or several)."""
    conv.state.task = "change_address"
    gate = orders.require(conv, "change_address")
    if gate:
        return gate

    conv.write_metric("MODIFY_ORDER_FLOW_INITIATED", write_once=True)
    flow.goto_step("Change Address", "caller verified")
    hint, conv.state.order_hint = conv.state.order_hint or "", ""
    order, matches, orders_ = orders.pick_order(conv, hint)
    if order:
        return address_reply(conv, order)
    if not orders_:
        return (
            "Say: \"I can't see any recent orders on your account. Is it possible you ordered with "
            'a different phone number, or as a guest?"'
        )
    if hint and orders.names_an_order(hint) and not matches:
        return orders.no_matching_order(orders_, conv, TOOL, hint)
    return (
        "If the caller has already said which order, call save_new_address with that as "
        "order_hint (and the new address if they gave it). Otherwise: "
        + orders.which_order_instruction(
            orders_, conv, TOOL, WHICH, matched=matches if hint and matches else None
        )
    )
