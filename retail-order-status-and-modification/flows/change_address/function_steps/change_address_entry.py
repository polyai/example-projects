from _gen import *  # <AUTO GENERATED>
from flows.change_address.functions.save_new_address import address_reply
from functions import idnv, orders


def change_address_entry(conv: Conversation, flow: Flow):
    """Entry gate: verify, then pick the order to re-address (none, one or several)."""
    conv.state.task = "change_address"
    gate = idnv.require(conv, "change_address")
    if gate:
        return gate

    conv.write_metric("MODIFY_ORDER_FLOW_INITIATED", write_once=True)
    flow.goto_step("Change Address", "caller verified")
    hint, conv.state.order_hint = conv.state.order_hint or "", ""
    order, _matches, orders_ = orders.pick_order(conv, hint)
    if order:
        return address_reply(conv, order)
    if not orders_:
        return "There are no recent orders on this account. Tell the caller and ask if there's anything else."
    return (
        "If the caller has already said which order (an item, or digits of the order number), "
        "call save_new_address with that as order_hint (and the new address if they gave it). "
        + orders.which_order_instruction(orders_, conv, "save_new_address")
    )
