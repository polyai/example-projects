from _gen import *  # <AUTO GENERATED>
import functions.address as address
import functions.api_client as api_client
import functions.idnv as idnv
import functions.orders as orders
import functions.sms as sms
from functions.handoff import handoff

READBACK_KEY = "address"
MAX_UNCLEAR = 3  # answers that can't be made out as an address; the last one transfers
TOOL = "save_new_address"
WHICH = "Which one is it about?"
NOT_SAVED_LINE = (
    "I'm sorry, I'm not able to take that address down. I'll put you through to the team, who "
    "can change it for you. One moment, please."
)
FAILED_LINE = (
    "I'm sorry, I couldn't change that just now. I'll put you through to the team, who can do "
    "it for you. One moment, please."
)
ASK_ADDRESS = "What's the new address, with the ZIP code?"
ASK_PART = {
    "zip": "And what's the ZIP code?",
    "number": "And what's the house or building number?",
}


def _pending(conv, order: dict) -> dict | None:
    change = conv.state.address_change
    if isinstance(change, dict) and change.get("order_number") == order["order_number"]:
        return change.get("address")
    return None


def _state(conv, next_line: str) -> str:
    return orders.call_state(conv, ["Task: change the delivery address"], next_line)


def _items(order: dict) -> str:
    return orders.short_items(order)


def address_reply(conv, order: dict) -> str:
    """What to say once the order is known: why it can't change, or ask for the address."""
    blocked = orders.address_block(order)
    if blocked:
        conv.write_metric("MODIFY_ORDER_NOT_ALLOWED")
        offer, follow = "", ""
        if orders.in_transit(order) and orders.tracking_url(order):
            offer = " " + sms.offer(conv, "tracking_link", order["order_number"])
            follow = (
                " A yes to the text offer → call start_send_sms with sms_id='tracking_link' and "
                "caller_agreed='true'."
            )
        return (
            f'Say: "{blocked}{offer}" Don\'t offer a transfer unless they ask.{follow}\n\n'
            + _state(conv, "Help with whatever they want next.")
        )
    w = orders._Words(order["items"])
    lead = f"Your {_items(order)} {w.hasnt} shipped yet, so I can change where {w.its_short} going."
    return (
        f"If the caller has already given the new address, call {TOOL} with it now. Otherwise "
        f'say: "{lead} {ASK_ADDRESS}" (just "What\'s the new address?" if that would repeat '
        f"what they've said). If they ask whether changing it changes when it arrives: \"It "
        f"shouldn't, as it hasn't shipped yet.\" Don't say where it's going now unless they ask: "
        f"{order['shipping_address']}. {orders.call_again(TOOL)}\n\n"
        + _state(conv, "Get the new delivery address.")
    )


def confirm_question(order: dict, addr: dict, only: list[str] | None = None) -> str:
    """The readback and the question, built in code: 'So that's four five Elm Street, New
    York, New York, one zero zero zero two. Shall I send your backpack there instead?'.
    After a correction, only what changed."""
    if only is not None:
        changed = address.spoken(addr, only)
        return f"{changed[0].upper()}{changed[1:]}. Shall I send it there instead?"
    return f"So that's {address.spoken(addr)}. Shall I send your {_items(order)} there instead?"


def _readback(conv, order: dict, addr: dict) -> dict:
    """The readback and its question, spoken as written: the model dropped the repeated "New
    York, New York" and the street type when it voiced the readback itself."""
    fields = address.readback_fields(addr)
    changed, mode = orders.readback_text(
        conv, READBACK_KEY, [("order", order["order_number"])] + fields
    )
    only = (
        None
        if mode == "full" or "order" in changed
        else [c for c in changed if c != "order"]
    )
    question = confirm_question(order, addr, only)
    orders.asked(conv, READBACK_KEY, question)
    lead = "Sorry about that. " if only else ""
    return {"utterance": f"{lead}{question}"}


@func_description(
    "Pick the order, take the new delivery address, read it back and save it once the caller has agreed to the readback question this tool gave you. Call it whenever the caller says which order, gives or corrects the address, or answers the question, even if it's the same as before."
)
@func_parameter(
    "order_hint",
    "What the caller said that picks out the order: an item ('the backpack'), or digits of the order number. Empty string if it's the order already being discussed.",
)
@func_parameter(
    "new_address",
    "The new delivery address as the caller said it, with number words as digits, e.g. '45 Elm Street, New York, 10002'. Only a ZIP code or a house number if that's all they gave. Empty string if they gave none this time.",
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply agreed to the readback question this tool returned. 'Okay', 'sure', 'sounds good' or 'go on' in answer to that question is agreement; a correction, an answer to something else, or real hesitation is not. Otherwise 'false'.",
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
        return orders.require(conv, "change_address")

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
    if orders.address_block(order):
        return address_reply(conv, order)

    said = str(new_address or "").strip()
    addr = _pending(conv, order)
    if said:
        parsed = address.parse(said)
        merged = address.merge(addr, parsed)
        if not address.recognisable(parsed):
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
                f"NOT A FULL ADDRESS (attempt {misses} of {MAX_UNCLEAR}): ask for the new address "
                f"again, with the house number, street, city and ZIP code. {orders.call_again(TOOL)}"
            )
        conv.state.address_misses = 0
        conv.state.address_change = {
            "order_number": order["order_number"],
            "address": merged,
        }
        addr = merged
    if not addr:
        return f'Ask: "{ASK_ADDRESS}" {orders.call_again(TOOL)}'
    gap = address.missing(addr)
    if gap:
        if gap == "street":
            return f'Ask: "{ASK_ADDRESS}" {orders.call_again(TOOL)}'
        return (
            f'Ask only for the missing part: "{ASK_PART[gap]}" Pass just what they say as '
            f"new_address. {orders.call_again(TOOL)}"
        )

    fields = [("order", order["order_number"])] + address.readback_fields(addr)
    if not orders.readback_is_current(conv, READBACK_KEY, fields):
        return _readback(conv, order, addr)
    if str(caller_confirmed).strip().lower() != "true":
        question = orders.last_question(conv, READBACK_KEY)
        orders.asked(conv, READBACK_KEY, question)
        return (
            f'NOT SAVED YET. Answer anything they asked, then ask again: "{question}" '
            f"{orders.YES_LINE}: call {TOOL} with caller_confirmed='true'.\n\n"
            + _state(conv, "Wait for the caller's answer to the readback.")
        )
    if orders.same_turn_as_ask(conv, READBACK_KEY):
        return orders.wait_for_answer(conv, READBACK_KEY)

    try:
        api_client.update_delivery_address(
            conv, order["order_number"], address.formatted(addr)
        )
    except Exception:
        conv.log.error("update_delivery_address failed", exc_info=True)
        return handoff(conv, "MODIFY_ORDER_FAIL", FAILED_LINE, "CUSTOMER_SERVICE")

    conv.write_metric("ORDER_ADDRESS_MODIFIED")
    conv.state.task = ""
    conv.state.address_change = None
    orders.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    return {
        "utterance": (
            f"I've changed the delivery address for your {_items(order)}, and you'll get an email "
            f"confirming it. {orders.ANYTHING_ELSE}"
        )
    }
