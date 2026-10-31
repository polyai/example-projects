from functions.handoff import handoff

from _gen import *  # <AUTO GENERATED>
from functions import idnv, orders

COLLEAGUE_LINE = (
    "I've found your order, but a colleague will need to help you with it. One moment while I "
    "put you through."
)


def _next_line(order: dict) -> str:
    if orders.tracking_url(order):
        return (
            "Then offer to text them a tracking link with the latest details (if they want it, "
            "call start_send_sms with sms_id='tracking_link')."
        )
    return "Then ask if there's anything else you can help with."


def _one(conv, order: dict) -> str | dict:
    reason = orders.needs_colleague(order)
    if reason:
        return handoff(conv, reason, COLLEAGUE_LINE, "CUSTOMER_SERVICE")
    conv.write_metric("ORDER_STATUS_FLOW_SUCCESSFUL", write_once=True)
    return (
        f"Tell the caller, naturally and briefly, about {orders.describe_order(order, conv)}: "
        f"{orders.status_text(order, conv)} Mention the items, not the order number. "
        f"{_next_line(order)}\n\n"
        + orders.call_state(
            conv,
            ["Task: track an order"],
            "Answer any follow-up about this order, or help with the next thing.",
        )
    )


def _summary(conv, orders_: list[dict]) -> str:
    lines = []
    for order in orders_:
        if orders.needs_colleague(order):
            lines.append(
                f"{orders.describe_order(order, conv)}: a colleague needs to help with this one; "
                "offer to put them through (handoff_reason=ORDER_ON_HOLD) if it's the one they mean"
            )
        else:
            lines.append(
                f"{orders.describe_order(order, conv)}: {orders.status_text(order, conv)}"
            )
    conv.write_metric("ORDER_STATUS_FLOW_SUCCESSFUL", write_once=True)
    return (
        f"The caller has {len(orders_)} recent orders. Give a short update on each, one or two "
        "sentences per order, naming the items rather than order numbers:\n- "
        + "\n- ".join(lines)
        + "\nThen ask if they'd like more detail on one of them.\n\n"
        + orders.call_state(
            conv,
            ["Task: track an order"],
            "If they pick an order, call get_order_status with what they say about it.",
        )
    )


@func_description(
    "Look up the status of the caller's order and say what to tell them. Call it whenever the caller asks about an order or says which order they mean."
)
@func_parameter(
    "order_hint",
    "Whatever the caller said that picks out the order: an item ('the running shoes'), or digits of the order number as they said them ('ending seven five six one'). 'all' if they want every order. Empty string if they haven't said.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me pull that up.", 3), ("Just a moment.", 3)],
)
def get_order_status(conv: Conversation, flow: Flow, order_hint: str):
    if not idnv.is_verified(conv):
        return idnv.require(conv, "track_order")

    order, matches, orders_ = orders.pick_order(conv, order_hint)
    if not orders_:
        conv.write_metric("NO_ORDERS_FOUND", "track")
        return (
            "There are no recent orders on this account. Tell the caller, and ask if they might "
            "have ordered with a different phone number or as a guest; if they want to check, "
            "a colleague can search by email (handoff_reason=ORDER_NOT_FOUND)."
        )
    if order:
        return _one(conv, order)
    if orders.names_an_order(order_hint or "") and not matches:
        return orders.no_matching_order(orders_, conv, "get_order_status")
    if len(matches) <= orders.MAX_ORDERS_SUMMARISED:
        return _summary(conv, matches)
    return orders.which_order_instruction(
        orders_, conv, "get_order_status", matched=None
    )
