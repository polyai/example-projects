"""Order rules, order selection, status wording, readbacks and the call-state block,
shared by every order task.

The flows stay one prompt and a tool each because the rules live here:
- which order the caller means, from an item ("the running shoes") or digits of
  the order number ("ending 7561"), in code (match_orders / pick_order);
- what each status means for the caller, and which statuses need a colleague
  (status_text / needs_colleague);
- what can be cancelled or re-addressed (cancel_block / address_block);
- what the agent reads back: everything the first time, then only what changed
  (readback_text), and whether a yes came in the same turn as the readback, before
  the caller could answer (asked / same_turn_as_ask);
- the CALL STATE block every tool response ends with. On voice a step prompt is
  rendered once, when the step is entered, so state shown in the prompt would
  freeze; the latest tool response is always current.
"""

from _gen import *  # <AUTO GENERATED>
import re
from datetime import date, timedelta

import functions.api_client as api
import functions.idnv as idnv
import functions.store_info as store_info
from functions.handoff import handoff

MAX_ORDERS_SUMMARISED = 3
MAX_ORDER_MISSES = (
    2  # descriptions that match no order on the account; the last one transfers
)
NO_MATCH_LINE = (
    "I'm sorry, I can't find that order on your account. Let me put you through to a colleague "
    "who can look into it. One moment please."
)
_ACKS = {
    "okay",
    "ok",
    "yes",
    "yeah",
    "yep",
    "sure",
    "no",
    "nope",
    "um",
    "uh",
    "hmm",
    "right",
}
_NUMBER_WORDS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
]
_DIGIT_TOKENS = {w: str(i) for i, w in enumerate(_NUMBER_WORDS)} | {"oh": "0"}
_ALL_WORDS = {"all", "both", "every", "everything", "each"}
_CURRENT_WORDS = {"current", "same", "that", "this", "it", "one", "order", "the"}
_STOP_WORDS = {
    "the", "a", "an", "my", "one", "order", "orders", "with", "for", "of", "and", "that", "this",
    "ending", "ends", "in", "number", "item", "items", "i", "ordered", "pair", "please", "some",
}  # fmt: skip


@func_description("[UTIL] Order rules and wording helpers, not callable directly")
def orders(conv: Conversation):
    return "Order helpers module."


# --- Speaking dates, items and orders ---------------------------------------


def today(conv) -> date:
    try:
        return date.fromisoformat(conv.state.today_iso)
    except (TypeError, ValueError):
        return date.today()


def _ordinal(n: int) -> str:
    suffix = (
        "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


def say_date(iso: str, conv) -> str:
    day = date.fromisoformat(iso[:10])
    text = f"{day.strftime('%A')}, {day.strftime('%B')} {_ordinal(day.day)}"
    now = today(conv)
    if day == now:
        return f"today, {text}"
    if day == now + timedelta(days=1):
        return f"tomorrow, {text}"
    if day == now - timedelta(days=1):
        return f"yesterday, {text}"
    return text


def say_digits(digits: str) -> str:
    return " ".join(_NUMBER_WORDS[int(d)] for d in digits if d.isdigit())


def last_four(order: dict) -> str:
    return re.sub(r"\D", "", order["order_number"])[-4:]


def item_phrase(item: dict) -> str:
    name = f"{item['brand']} {item['name']}".strip()
    if item["category"] == "Footwear" and item["size"]:
        name += f" in a size {item['size']}"
    qty = int(item.get("quantity") or 1)
    if qty > 1:
        name = f"{_NUMBER_WORDS[qty] if qty < 10 else qty} {name}"
    return name


def _join(parts: list[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _plural(items: list[dict]) -> bool:
    return (
        len(items) > 1
        or int(items[0].get("quantity") or 1) > 1
        or items[0]["name"].lower().endswith("s")
    )


def describe_order(order: dict, conv) -> str:
    """'the order from Saturday, October 17th, ending seven five six one, with the
    Nike Running Shoes in a size 10 and Nike Sport Socks'"""
    items = _join([item_phrase(i) for i in order["items"]])
    return (
        f"the order from {say_date(order['placed'], conv)}, ending {say_digits(last_four(order))}, "
        f"with the {items}"
    )


def short_order(order: dict) -> str:
    return f"the {_join([i['name'] for i in order['items']])} order"


# --- The caller's orders and which one they mean -----------------------------


def caller_orders(conv) -> list[dict]:
    customer = idnv.customer(conv)
    if not customer:
        return []
    return api.list_orders(conv, customer["id"])


def selected_order(conv, orders_: list[dict] | None = None) -> dict | None:
    wanted = conv.state.selected_order_number
    if not wanted:
        return None
    return next(
        (o for o in (orders_ or caller_orders(conv)) if o["order_number"] == wanted),
        None,
    )


def select(conv, order: dict | None) -> None:
    conv.state.selected_order_number = order["order_number"] if order else ""
    if order:
        conv.state.order_misses = 0


def _digit_runs(text: str) -> list[str]:
    runs, current = [], ""
    for token in re.findall(r"[a-z]+|\d", text.lower()):
        digit = token if token.isdigit() else _DIGIT_TOKENS.get(token)
        if digit is None:
            if current:
                runs.append(current)
            current = ""
            continue
        current += digit
    if current:
        runs.append(current)
    return [r for r in runs if len(r) >= 3]


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def _order_words(order: dict) -> set[str]:
    words = set()
    for item in order["items"]:
        text = f"{item['brand']} {item['name']} {item['category']}".lower()
        words |= {_stem(w) for w in re.findall(r"[a-z]+", text)}
    if order["fulfilment"] == "pickup":
        words |= {"pickup", "pick", "store", "collect"}
    return words


def match_orders(orders_: list[dict], hint: str) -> list[dict]:
    """The orders a caller's description fits: digits of the order number (three or
    more, matched against the end of the number first), or words from the items."""
    text = (hint or "").strip().lower()
    if not text:
        return []
    words = re.findall(r"[a-z]+", text)
    if _ALL_WORDS & set(words):
        return list(orders_)
    for run in _digit_runs(text):
        numbers = {
            o["order_number"]: re.sub(r"\D", "", o["order_number"]) for o in orders_
        }
        ending = [o for o in orders_ if numbers[o["order_number"]].endswith(run)]
        if ending:
            return ending
        inside = [o for o in orders_ if run in numbers[o["order_number"]]]
        if inside:
            return inside
    wanted = {
        _stem(w) for w in words if w not in _STOP_WORDS and w not in _NUMBER_WORDS
    }
    if not wanted:
        return []
    scored = [(len(wanted & _order_words(o)), o) for o in orders_]
    best = max((s for s, _ in scored), default=0)
    return [o for s, o in scored if best and s == best]


def names_an_order(text: str) -> bool:
    """Whether a hint names anything (digits, or a word that isn't filler like 'my order' or
    'okay')."""
    words = set(re.findall(r"[a-z]+", text.lower()))
    return bool(
        _digit_runs(text) or words - _STOP_WORDS - _CURRENT_WORDS - _ALL_WORDS - _ACKS
    )


def pick_order(conv, hint: str) -> tuple[dict | None, list[dict], list[dict]]:
    """(the order the task is about, or None; every order that fits; all the caller's
    orders). An empty or 'current' hint keeps the order already being discussed, and
    a caller with a single order needs no hint."""
    orders_ = caller_orders(conv)
    text = (hint or "").strip().lower()
    current = selected_order(conv, orders_)
    words = set(re.findall(r"[a-z]+", text))
    if not text or (words and words <= _CURRENT_WORDS and not re.search(r"\d", text)):
        if current:
            return current, [current], orders_
        if len(orders_) == 1:
            select(conv, orders_[0])
            return orders_[0], orders_, orders_
        return None, list(orders_), orders_
    matches = match_orders(orders_, text)
    if not matches and not names_an_order(text):
        return pick_order(conv, "")
    if len(matches) == 1:
        select(conv, matches[0])
        return matches[0], matches, orders_
    return None, matches, orders_


def listing(orders_: list[dict], conv) -> str:
    return "; ".join(describe_order(o, conv) for o in orders_)


def call_again(task_tool: str) -> str:
    """The last sentence of every return that needs another answer from the caller, so the
    model passes the answer to the tool (Dialog-RSN-1 won't repeat a call on its own)."""
    return f"Then call {task_tool} again with whatever they say, even if it's the same as before."


def which_order_instruction(
    orders_: list[dict], conv, task_tool: str, matched=None
) -> str:
    """Ask which order the caller means: none named yet, or a description that fits several."""
    if matched:
        lead = "That fits more than one order."
    else:
        lead = f"The caller has {len(orders_)} recent orders."
    return (
        f"{lead} Their orders: {listing(orders_, conv)}. Ask which one they mean (an item, or the "
        f"last digits of the order number). {call_again(task_tool)}"
    )


def no_matching_order(orders_: list[dict], conv, task_tool: str) -> str | dict:
    """The caller described an order that isn't on the account: a miss, counted here. The
    attempt is named, and the last miss transfers."""
    misses = int(conv.state.order_misses or 0) + 1
    conv.state.order_misses = misses
    if misses >= MAX_ORDER_MISSES:
        conv.state.order_misses = 0
        conv.write_metric("ORDER_NOT_MATCHED")
        return handoff(conv, "ORDER_NOT_FOUND", NO_MATCH_LINE, "CUSTOMER_SERVICE")
    return (
        f"NO MATCHING ORDER (attempt {misses} of {MAX_ORDER_MISSES}): that doesn't match any order "
        f"on the account. Their orders: {listing(orders_, conv)}. Ask which one they mean (an "
        f"item, or the last digits of the order number). {call_again(task_tool)}"
    )


# --- Status ------------------------------------------------------------------


def needs_colleague(order: dict) -> str:
    """A reason code when only a colleague can help with this order, else ''."""
    if order.get("hold"):
        return "ORDER_ON_HOLD"
    cancelled = [i for i in order["items"] if i["status"] == api.CANCELLED]
    if any(
        i["cancel_reason"] not in ("out_of_stock", "customer_request")
        for i in cancelled
    ):
        return "ORDER_CANCELLED_BY_STORE"
    return ""


def _group_sentence(status: str, items: list[dict], order: dict, conv) -> str:
    names = _join([f"the {item_phrase(i)}" for i in items])
    plural = _plural(items)
    have, are, were = ("have", "are", "were") if plural else ("has", "is", "was")
    first = items[0]
    if status == api.SHIPPED:
        text = f"{names} {have} shipped with {first['carrier']}"
        if first["tracking_status"]:
            text += f" and {are} {first['tracking_status']}"
        if first["last_scan"]:
            text += f", last scanned in {first['last_scan']}"
        if first["expected_delivery"]:
            text += f", and should arrive {say_date(first['expected_delivery'], conv)}"
        return text + "."
    if status == api.DELIVERED:
        when = (
            f" on {say_date(first['completed_on'], conv)}"
            if first["completed_on"]
            else ""
        )
        return f"{names} {were} delivered{when}."
    if status == api.READY_FOR_PICKUP:
        return f"{names} {are} ready to pick up in store. {store_info.attr(conv, 'instore_pickup_info')}".strip()
    if status == api.PICKED_UP:
        when = (
            f" on {say_date(first['completed_on'], conv)}"
            if first["completed_on"]
            else ""
        )
        return f"{names} {were} picked up{when}."
    if status == api.CANCELLED:
        if first["cancel_reason"] == "customer_request":
            return f"{names} {were} cancelled at your request."
        return f"{names} {were} cancelled. {store_info.CANCELLED_OUT_OF_STOCK}"
    if order["fulfilment"] == "pickup":
        return (
            f"{names} {are} still being prepared. {store_info.PROCESSING_PICKUP} "
            f"{store_info.attr(conv, 'instore_pickup_info')}"
        ).strip()
    return f"{names} {are} still being processed. {store_info.PROCESSING_SHIP}"


def status_text(order: dict, conv) -> str:
    """What to tell the caller about one order, grouping items that share a status."""
    groups: dict[tuple, list[dict]] = {}
    for item in order["items"]:
        key = (
            item["status"],
            item["carrier"],
            item["expected_delivery"],
            item["completed_on"],
        )
        groups.setdefault(key, []).append(item)
    return " ".join(
        _group_sentence(key[0], items, order, conv) for key, items in groups.items()
    )


def tracking_url(order: dict) -> str:
    return next(
        (
            i["tracking_url"]
            for i in order["items"]
            if i["status"] == api.SHIPPED and i["tracking_url"]
        ),
        "",
    )


# --- What can change ----------------------------------------------------------


def _any_status(order: dict, statuses: tuple) -> bool:
    return any(i["status"] in statuses for i in order["items"])


def cancel_block(order: dict) -> str:
    """Why this order can't be cancelled here, or '' if it can."""
    if all(i["status"] == api.CANCELLED for i in order["items"]):
        return "This order is already cancelled."
    if _any_status(order, (api.SHIPPED, api.DELIVERED, api.PICKED_UP)):
        return "Part or all of this order has already shipped, so it can't be cancelled; it can be returned once it arrives."
    if _any_status(order, (api.READY_FOR_PICKUP,)):
        return (
            "This order is already waiting in store. If they don't want it, they can simply "
            "not collect it, or a colleague can cancel it."
        )
    return ""


def address_block(order: dict) -> str:
    """Why this order's delivery address can't be changed, or '' if it can."""
    if order["fulfilment"] == "pickup":
        return "This is an in-store pickup order, so it has no delivery address."
    if all(i["status"] == api.CANCELLED for i in order["items"]):
        return "This order is cancelled."
    if _any_status(order, (api.SHIPPED, api.DELIVERED, api.PICKED_UP)):
        return (
            "Part or all of this order has already shipped, so the delivery address can't be "
            "changed. The carrier's tracking page may let them redirect the parcel."
        )
    return ""


# --- Readbacks ------------------------------------------------------------------


def readback_text(conv, key: str, fields: list[tuple[str, str]]) -> tuple[str, str]:
    """What to read back for `key`: every field the first time, then only the
    fields whose value changed since the last readback.

    Returns (text, mode): mode is "full" the first time, "changes" when some
    fields changed, and "none" when the caller has already heard all of it, so
    a write tool can go ahead on a "yes".
    """
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    last = store.get(key)
    current = {label: value for label, value in fields if value}
    conv.state.readbacks = {**store, key: current}
    if last is None:
        return "; ".join(current.values()), "full"
    changed = [value for label, value in current.items() if last.get(label) != value]
    return "; ".join(changed), ("changes" if changed else "none")


def readback_is_current(conv, key: str, fields: list[tuple[str, str]]) -> bool:
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    current = {label: value for label, value in fields if value}
    return store.get(key) == current


def forget_readback(conv, key: str) -> None:
    store = dict(conv.state.readbacks) if isinstance(conv.state.readbacks, dict) else {}
    store.pop(key, None)
    conv.state.readbacks = store
    turns = (
        dict(conv.state.readback_turns)
        if isinstance(conv.state.readback_turns, dict)
        else {}
    )
    turns.pop(key, None)
    conv.state.readback_turns = turns


def _turn(conv):
    """The history's length, used only as a same-turn marker: at tool time the history
    holds earlier turns, so it grows once the caller has replied. None if unavailable."""
    try:
        return len(conv.history)
    except Exception:
        return None


def asked(conv, key: str) -> None:
    """Record the turn in which a write tool's readback asked its yes-or-no question."""
    turns = (
        dict(conv.state.readback_turns)
        if isinstance(conv.state.readback_turns, dict)
        else {}
    )
    turns[key] = _turn(conv)
    conv.state.readback_turns = turns


def same_turn_as_ask(conv, key: str) -> bool:
    """True while the caller can't have answered the readback yet (same turn)."""
    turns = (
        conv.state.readback_turns if isinstance(conv.state.readback_turns, dict) else {}
    )
    turn = _turn(conv)
    return turn is not None and turns.get(key) == turn


def yes_no_question(action: str) -> str:
    """The whole spoken confirmation for a write: the action and the key value only."""
    return f"Shall I {action}, yes or no?"


def confirm_instruction(
    question: str, tool: str, param: str = "caller_confirmed"
) -> str:
    """Tell the model to ask `question` as the readback, with nothing added, and that only a
    clear yes to it lets the tool write."""
    return (
        f'Ask the caller just this, in about these words: "{question}" '
        "Don't add dates, order numbers or other details. Wait for the answer. Only a clear yes to that question counts: "
        f"then call {tool} with {param}='true'."
    )


def wait_for_answer(tool: str) -> str:
    return (
        "NOT DONE YET: wait for the caller's answer to the yes-or-no question, then call "
        f"{tool} again."
    )


# --- Call state -----------------------------------------------------------------


def call_state(conv, task_lines: list[str], next_line: str) -> str:
    order = selected_order(conv)
    lines = [
        "CALL STATE (this replaces any earlier copy; never read it aloud)",
        f"- {idnv.state_line(conv)}",
        "- Order: " + (describe_order(order, conv) if order else "none chosen yet"),
    ]
    lines += [f"- {line}" for line in task_lines if line]
    lines.append(f"NEXT: {next_line}")
    return "\n".join(lines)
