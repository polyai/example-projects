from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
import functions.orders as orders
import functions.sms as sms
import functions.store_info as store_info
from functions.handoff import handoff
from functions.start_cancel_order import TRANSFER_LINE, cancellation_enabled

READBACK_KEY = "cancel"
TOOL = "process_cancel_order"
WHICH = "Which one is it about?"
FAILED_LINE = (
    "I'm sorry, I couldn't cancel that just now. I'll put you through to the team, who can do "
    "it for you. One moment, please."
)


def _fields(order: dict) -> list[tuple[str, str]]:
    return [("order", order["order_number"])]


def _state(conv, next_line: str) -> str:
    return orders.call_state(conv, ["Task: cancel an order"], next_line)


def confirm_question(order: dict, orders_: list[dict] | None = None) -> str:
    """The readback and the question: the items, and the last four digits only when the
    items alone don't pick out the order."""
    name = f"your order with the {orders.items_phrase(order['items'])}"
    if orders_ and any(
        o["order_number"] != order["order_number"] and orders.same_items(o, order)
        for o in orders_
    ):
        name += f", ending {orders.say_digits(orders.last_four(order))}"
    return f"That's {name}. Shall I cancel it for you?"


def _readback(conv, order: dict, again: bool) -> str:
    question = confirm_question(order, orders.caller_orders(conv))
    orders.readback_text(conv, READBACK_KEY, _fields(order))
    orders.asked(conv, READBACK_KEY, question)
    if again:
        ask = (
            "Answer anything they asked first (if it's the charge: \"any pending charge will drop "
            f'off your card within {store_info.CHARGE_DAYS}"), then ask: "Shall I go ahead and '
            'cancel it?"'
        )
    else:
        ask = (
            f'Read it back and ask, in these words: "{question}" If they ask whether they\'ll be '
            f'charged: "No, any pending charge will drop off your card within {store_info.CHARGE_DAYS}." '
            'then ask "Shall I go ahead and cancel it?"'
        )
    return (
        f"NOT CANCELLED YET. {ask} Wait for the answer. {orders.YES_LINE}: call {TOOL} with "
        "caller_confirmed='true'. A question back, or real hesitation, isn't: answer it, or "
        f"wait, then call {TOOL} again with caller_confirmed='false'. If they'd rather keep it, "
        'say "No problem, I\'ll leave your order as it is."\n\n'
        + _state(conv, "Wait for the caller's answer to the cancel question.")
    )


def cancel_reply(conv, order: dict) -> str:
    """What to say once the order is known: why it can't be cancelled, or the readback."""
    blocked = orders.cancel_block(order)
    if blocked:
        conv.write_metric("CANCEL_ORDER_NOT_ALLOWED")
        offer = ""
        if orders.items_with(
            order, (orders.api.SHIPPED, orders.api.DELIVERED)
        ) and store_info.attr(conv, "returns_url"):
            offer = " " + sms.offer(conv, "returns_portal")
        follow = (
            " A yes to the text offer → call start_send_sms with sms_id='returns_portal' and "
            "caller_agreed='true'."
            if offer
            else ""
        )
        return (
            f'Say: "{blocked}{offer}" Don\'t offer a transfer unless the line above does or they '
            f"ask.{follow}\n\n" + _state(conv, "Help with whatever they want next.")
        )
    return _readback(conv, order, again=False)


@func_description(
    "Pick the order to cancel, read it back, and cancel it once the caller has agreed to the readback question this tool gave you. Call it whenever the caller says which order or answers the question, even if it's the same as before."
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
    "'true' only if the caller's latest reply agreed to the readback question this tool returned. 'Okay', 'sure', 'sounds good' or 'go on' in answer to that question is agreement; an answer to something else, a question back, or real hesitation is not. Otherwise 'false'.",
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
        return orders.require(conv, "cancel_order")

    before = conv.state.selected_order_number
    order, matches, orders_ = orders.pick_order(conv, order_hint)
    if not order:
        if not orders_:
            return "Say: \"I can't see any recent orders on your account.\" Then ask if there's anything else."
        named = orders.names_an_order(order_hint)
        if named and not matches:
            return orders.no_matching_order(orders_, conv, TOOL, order_hint)
        return orders.which_order_instruction(
            orders_, conv, TOOL, WHICH, matched=matches if named else None
        )
    if order["order_number"] != before:
        orders.forget_readback(conv, READBACK_KEY)

    if orders.cancel_block(order):
        return cancel_reply(conv, order)
    if not orders.readback_is_current(conv, READBACK_KEY, _fields(order)):
        return _readback(conv, order, again=False)
    if str(caller_confirmed).strip().lower() != "true":
        return _readback(conv, order, again=True)
    if orders.same_turn_as_ask(conv, READBACK_KEY):
        return orders.wait_for_answer(conv, READBACK_KEY)
    if not cancellation_enabled(conv):
        return handoff(conv, "CANCEL_ORDER", TRANSFER_LINE, "CUSTOMER_SERVICE")

    try:
        api_client.cancel_order(conv, order["order_number"], (reason or "").strip())
    except Exception:
        conv.log.error("cancel_order failed", exc_info=True)
        return handoff(conv, "CANCEL_ORDER_FAIL", FAILED_LINE, "CUSTOMER_SERVICE")

    if reason and reason.strip():
        conv.write_metric("CANCEL_REASON", reason.strip()[:100])
    conv.write_metric("CANCEL_ORDER_FLOW_SUCCESSFUL")
    conv.state.task = ""
    orders.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    name = orders.short_items(order)
    done = (
        f"I've cancelled your {name} order. You'll get a confirmation email shortly, and any "
        f"pending charge will drop off your card within {store_info.CHARGE_DAYS}. "
        f"{orders.ANYTHING_ELSE}"
    )
    short = (
        f"I've cancelled your {name} order, and you'll get a confirmation email shortly. "
        f"{orders.ANYTHING_ELSE}"
    )
    return (
        f'CANCELLED. Say: "{done}" If you\'ve already told the caller about the charge on this '
        f'call, say this instead: "{short}"'
    )
