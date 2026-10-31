from _gen import *  # <AUTO GENERATED>
import re

import functions.api_client as api_client
import functions.idnv as idnv
import functions.orders as orders
from functions.handoff import handoff

READBACK_KEY = "address"
MAX_UNCLEAR = 3  # answers that aren't a full address; the last one transfers
TOOL = "save_new_address"
NOT_SAVED_LINE = (
    "I'm sorry, I'm not able to take that address down. Let me put you through to a colleague "
    "who can change it for you. One moment please."
)


def _pending(conv, order: dict) -> str:
    change = conv.state.address_change
    if isinstance(change, dict) and change.get("order_number") == order["order_number"]:
        return change.get("address", "")
    return ""


def _fields(conv, order: dict, address: str) -> list[tuple[str, str]]:
    return [
        ("order", f"the new delivery address for {orders.short_order(order)}"),
        ("address", f"is {address}" if address else ""),
    ]


WAITING = "Wait for the caller's yes or no to changing the delivery address."


def confirm_question(order: dict, address: str) -> str:
    """What the caller hears before an address change: the order's items and the new address."""
    return orders.yes_no_question(
        f"deliver {orders.short_order(order)} to {address} instead"
    )


def _ask(order: dict, address: str) -> str:
    return orders.confirm_instruction(confirm_question(order, address), TOOL)


def _state(conv, order: dict | None, next_line: str) -> str:
    address = _pending(conv, order) if order else ""
    return orders.call_state(
        conv,
        [
            "Task: change the delivery address",
            "New address: " + (address or "not given yet"),
        ],
        next_line,
    )


_NUMBER_WORDS = set(
    "zero oh one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty "
    "ninety hundred thousand".split()
)


def looks_like_address(text: str) -> bool:
    """A street number (digits or spoken, e.g. 'forty-five') and at least two more words
    (street, city or ZIP)."""
    words = re.findall(r"[A-Za-z0-9]+", (text or "").lower())
    has_number = bool(re.search(r"\d", text or "")) or bool(_NUMBER_WORDS & set(words))
    return has_number and len(words) >= 3


def address_reply(conv, order: dict) -> str:
    """What to say once the order is known: why it can't change, or ask for the address."""
    blocked = orders.address_block(order)
    if blocked:
        conv.write_metric("MODIFY_ORDER_NOT_ALLOWED")
        return (
            f"This order's address can't be changed: {blocked} Tell the caller that kindly, and "
            "don't offer a transfer unless they ask for one.\n\n"
            + _state(conv, order, "Help with whatever they want next.")
        )
    return (
        f"It's {orders.describe_order(order, conv)}, going to {order['shipping_address']}. If the "
        "caller has already given the new address, call save_new_address with it now; otherwise "
        "ask for the new delivery address.\n\n"
        + _state(conv, order, "Get the new delivery address.")
    )


@func_description(
    "Pick the order, take the new delivery address and save it once the caller has said yes to the readback. Call it whenever the caller says which order or gives or corrects the address, even if it's the same as before."
)
@func_parameter(
    "order_hint",
    "What the caller said that picks out the order: an item ('the backpack'), or digits of the order number. Empty string if it's the order already being discussed.",
)
@func_parameter(
    "new_address",
    "The full new delivery address as the caller said it, e.g. '45 Elm Street, New York, NY 10002'. Empty string if they didn't give one this time.",
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
def save_new_address(
    conv: Conversation,
    flow: Flow,
    order_hint: str,
    new_address: str,
    caller_confirmed: str,
):
    if not idnv.is_verified(conv):
        return idnv.require(conv, "change_address")

    order, matches, orders_ = orders.pick_order(conv, order_hint)
    if not order:
        if not orders_:
            return "There are no recent orders on this account. Tell the caller."
        named = orders.names_an_order(order_hint)
        if named and not matches:
            return orders.no_matching_order(orders_, conv, TOOL)
        return orders.which_order_instruction(
            orders_, conv, TOOL, matched=matches if named else None
        )
    if orders.address_block(order):
        return address_reply(conv, order)

    address = (new_address or "").strip()
    if address:
        if not looks_like_address(address):
            misses = int(conv.state.address_misses or 0) + 1
            conv.state.address_misses = misses
            if misses >= MAX_UNCLEAR:
                conv.state.address_misses = 0
                return handoff(
                    conv,
                    "MODIFY_ORDER_ADDRESS_NOT_CAPTURED",
                    NOT_SAVED_LINE,
                    "CUSTOMER_SERVICE",
                )
            return (
                f"NOT A FULL ADDRESS (attempt {misses} of {MAX_UNCLEAR}): ask for the street "
                f"number and name, the city and the ZIP code. {orders.call_again(TOOL)}"
            )
        conv.state.address_misses = 0
        conv.state.address_change = {
            "order_number": order["order_number"],
            "address": address,
        }
    address = _pending(conv, order)
    if not address:
        return f"Ask for the new delivery address. {orders.call_again(TOOL)}"

    fields = _fields(conv, order, address)
    if not orders.readback_is_current(conv, READBACK_KEY, fields):
        orders.readback_text(conv, READBACK_KEY, fields)
        orders.asked(conv, READBACK_KEY)
        return (
            f"NOT SAVED YET. {_ask(order, address)} A correction goes to save_new_address "
            "without it. Don't say it's updated.\n\n"
        ) + _state(conv, order, WAITING)
    if str(caller_confirmed).strip().lower() != "true":
        orders.asked(conv, READBACK_KEY)
        return f"NOT SAVED YET. {_ask(order, address)}\n\n" + _state(
            conv, order, WAITING
        )
    if orders.same_turn_as_ask(conv, READBACK_KEY):
        return orders.wait_for_answer(TOOL)

    try:
        api_client.update_delivery_address(conv, order["order_number"], address)
    except Exception:
        conv.log.error("update_delivery_address failed", exc_info=True)
        return handoff(
            conv,
            "MODIFY_ORDER_FAIL",
            "I'm sorry, I couldn't change that just now. Let me put you through to a colleague "
            "who can, one moment please.",
            "CUSTOMER_SERVICE",
        )

    conv.write_metric("ORDER_ADDRESS_MODIFIED")
    conv.state.task = ""
    conv.state.address_change = None
    orders.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    return (
        f"Saved. Tell the caller {orders.short_order(order)} will now go to the new address (don't "
        "read it again), and they'll get an email confirming the change. Then ask if there's "
        "anything else."
    )
