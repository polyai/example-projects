from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
import functions.orders as orders
import functions.store_info as store_info
from functions.handoff import handoff
from functions.start_cancel_order import TRANSFER_LINE, cancellation_enabled

READBACK_KEY = "cancel"


def _fields(conv, order: dict) -> list[tuple[str, str]]:
    return [("order", orders.short_order(order))]


def _state(conv, next_line: str) -> str:
    return orders.call_state(conv, ["Task: cancel an order"], next_line)


def cancel_reply(conv, order: dict) -> str:
    """What to say once the order is known: why it can't be cancelled, or the readback."""
    blocked = orders.cancel_block(order)
    if blocked:
        conv.write_metric("CANCEL_ORDER_NOT_ALLOWED")
        return (
            f"This order can't be cancelled: {blocked} Our policy: "
            f"{store_info.attr(conv, 'order_changes_info')} Tell the caller that kindly, and don't "
            "offer a transfer unless they ask for one.\n\n"
            + _state(conv, "Help with whatever they want next.")
        )
    orders.readback_text(conv, READBACK_KEY, _fields(conv, order))
    orders.asked(conv, READBACK_KEY)
    return (
        "NOT CANCELLED YET. "
        + _ask(order)
        + "\n\n"
        + _state(conv, "Wait for the caller's yes or no to cancelling this order.")
    )


def _ask(order: dict) -> str:
    return orders.confirm_instruction(confirm_question(order), "process_cancel_order")


def confirm_question(order: dict) -> str:
    """What the caller hears before a cancellation: the action and the items, nothing else."""
    return orders.yes_no_question(f"cancel {orders.short_order(order)}")


@func_description(
    "Pick the order to cancel and cancel it once the caller has said yes to the order this tool gave you to read back. Call it whenever the caller says which order, even if it's the same as before."
)
@func_parameter(
    "order_hint",
    "What the caller said that picks out the order to cancel: an item ('the backpack'), or digits of the order number as they said them. Empty string if it's the order you already read back.",
)
@func_parameter(
    "reason", "Why they're cancelling, if they said. Empty string otherwise."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question this tool's readback asked. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Okay, one moment.", 3), ("Just a moment.", 3)],
)
def process_cancel_order(
    conv: Conversation, flow: Flow, order_hint: str, reason: str, caller_confirmed: str
):
    if not idnv.is_verified(conv):
        return idnv.require(conv, "cancel_order")

    before = conv.state.selected_order_number
    order, matches, orders_ = orders.pick_order(conv, order_hint)
    if not order:
        if not orders_:
            return "There are no recent orders on this account. Tell the caller."
        named = orders.names_an_order(order_hint)
        if named and not matches:
            return orders.no_matching_order(orders_, conv, "process_cancel_order")
        return orders.which_order_instruction(
            orders_, conv, "process_cancel_order", matched=matches if named else None
        )
    if order["order_number"] != before:
        orders.forget_readback(conv, READBACK_KEY)

    if orders.cancel_block(order) or not orders.readback_is_current(
        conv, READBACK_KEY, _fields(conv, order)
    ):
        return cancel_reply(conv, order)
    if str(caller_confirmed).strip().lower() != "true":
        orders.asked(conv, READBACK_KEY)
        return (
            "NOT CANCELLED YET. "
            + _ask(order)
            + "\n\n"
            + _state(conv, "Wait for the caller's yes or no to cancelling this order.")
        )
    if orders.same_turn_as_ask(conv, READBACK_KEY):
        return orders.wait_for_answer("process_cancel_order")
    if not cancellation_enabled(conv):
        return handoff(conv, "CANCEL_ORDER", TRANSFER_LINE, "CUSTOMER_SERVICE")

    try:
        api_client.cancel_order(conv, order["order_number"], (reason or "").strip())
    except Exception:
        conv.log.error("cancel_order failed", exc_info=True)
        return handoff(
            conv,
            "CANCEL_ORDER_FAIL",
            "I'm sorry, I couldn't cancel that just now. Let me put you through to a colleague "
            "who can, one moment please.",
            "CUSTOMER_SERVICE",
        )

    if reason and reason.strip():
        conv.write_metric("CANCEL_REASON", reason.strip()[:100])
    conv.write_metric("CANCEL_ORDER_FLOW_SUCCESSFUL")
    conv.state.task = ""
    orders.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    return (
        f"Cancelled. Tell the caller {orders.short_order(order)} is cancelled. "
        f"{store_info.CANCELLED_BY_CALLER} Then ask if there's anything else."
    )
