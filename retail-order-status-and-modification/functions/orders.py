"""Order rules, order selection, status wording, readbacks and the call-state block,
shared by every order task.

The flows stay one prompt and a tool each because the rules live here:
- which order the caller means, from an item ("the backpack") or digits of the order
  number ("ending 7561"), in code (match_orders / pick_order);
- how orders are named: by their items, newest first, three at most, with the last four
  digits only when two orders hold the same items (listing / which_order_instruction);
- what each status means for the caller: one sentence per status group to say, and the
  details to give only if asked (status_parts); whether an order is late (late_days);
  which statuses need a colleague (needs_colleague);
- what can be cancelled or re-addressed, and the line that says why not
  (cancel_block / address_block);
- what the agent reads back (readback_text), and whether a yes came in the same turn as
  the readback, before the caller could answer (asked / same_turn_as_ask);
- the CALL STATE block every order return ends with. On voice a step prompt is rendered
  once, when the step is entered, so state shown in the prompt would freeze; the latest
  tool response is always current.
"""

from _gen import *  # <AUTO GENERATED>
import re
from datetime import date, timedelta

import functions.api_client as api
import functions.idnv as idnv
import functions.store_info as store_info
from functions.handoff import handoff

MAX_ORDERS_LISTED = 3
MAX_ORDER_MISSES = (
    2  # descriptions that match no order on the account; the last one transfers
)
# Business days past the expected date before a late order is offered to the team. A constant
# until a client gives their own policy.
LATE_BUSINESS_DAYS = 3
ANYTHING_ELSE = "Is there anything else I can help with?"
NO_MATCH_LINE = (
    "I'm sorry, I can't find that order. I'll put you through to the team, who can look into "
    "it. One moment, please."
)
# Asked when the caller ID is on more than one account (idnv's caller-ID question).
CALLER_ID_QUESTION = "Is the number you're calling from the one on your account?"
NUMBER_ASK = "Sure, I can help with that. What's the phone number on your account?"

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
_COUNT_WORDS = [
    "no",
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
    "about", "calling", "where", "is", "are", "was", "new", "where's", "s", "me", "to", "on",
}  # fmt: skip


@func_description("[UTIL] Order rules and wording helpers, not callable directly")
def orders(conv: Conversation):
    return "Order helpers module."


def require(conv, resume: str):
    """idnv's gate, with the design's question for the phone number."""
    gate = idnv.require(conv, resume, caller_id_question=CALLER_ID_QUESTION)
    if gate and gate.endswith("ask for the phone number on their account."):
        gate += f' Ask it in these words: "{NUMBER_ASK}"'
    return gate


# --- Speaking dates, digits and items -----------------------------------------


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
    """'today', 'tomorrow', 'yesterday'; 'Thursday' within the week; 'Thursday the 5th'
    within two weeks; then 'Saturday, December 12th'. Past: 'Saturday' within the week,
    'last Monday, the 26th' within two weeks. Never the year."""
    day = date.fromisoformat(iso[:10])
    delta = (day - today(conv)).days
    weekday = day.strftime("%A")
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    if delta == -1:
        return "yesterday"
    if 2 <= delta <= 6 or -6 <= delta <= -2:
        return weekday
    if 7 <= delta <= 13:
        return f"{weekday} the {_ordinal(day.day)}"
    if -13 <= delta <= -7:
        return f"last {weekday}, the {_ordinal(day.day)}"
    return f"{weekday}, {day.strftime('%B')} {_ordinal(day.day)}"


def on_date(iso: str, conv) -> str:
    """say_date with 'on' where English needs it: 'on Thursday', but 'tomorrow' and
    'last Monday, the 26th'."""
    said = say_date(iso, conv)
    if said in ("today", "tomorrow", "yesterday") or said.startswith("last "):
        return said
    return f"on {said}"


def say_digits(digits: str) -> str:
    return " ".join(_NUMBER_WORDS[int(d)] for d in digits if d.isdigit())


def last_four(order: dict) -> str:
    return re.sub(r"\D", "", order["order_number"])[-4:]


def _join(parts: list[str], word: str = "and") -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + f" {word} " + parts[-1]


def _list(parts: list[str], word: str = "and") -> str:
    """Orders in a list: 'the running shoes and socks, and the backpack'."""
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + f", {word} " + parts[-1]


def _item_name(item: dict, items: list[dict]) -> str:
    name = item["name"].lower()
    twins = [i for i in items if i["name"].lower() == name]
    if len(twins) > 1 and item["size"] and len({i["size"] for i in twins}) > 1:
        name += f" in a size {item['size']}"
    qty = int(item.get("quantity") or 1)
    if qty > 1:
        name = f"{_COUNT_WORDS[qty] if qty < 10 else qty} {name}"
    return name


def items_phrase(items: list[dict], brand: bool = True) -> str:
    """'Nike running shoes and socks' (brand on first mention), or 'running shoes and
    socks'. The size only when two items differ only by size."""
    names = [_item_name(i, items) for i in items]
    if not brand:
        return _join(names)
    brands = {i["brand"] for i in items}
    if len(brands) == 1 and items[0]["brand"]:
        return f"{items[0]['brand']} {_join(names)}"
    return _join(
        [f"{i['brand']} {n}".strip() for i, n in zip(items, names, strict=True)]
    )


def plural(items: list[dict]) -> bool:
    return (
        len(items) > 1
        or int(items[0].get("quantity") or 1) > 1
        or items[0]["name"].lower().endswith("s")
    )


class _Words:
    """Agreement for a group of items: 'is'/'are', 'it'/'them' and so on."""

    def __init__(self, items: list[dict]):
        p = plural(items)
        self.is_ = "are" if p else "is"
        self.was = "were" if p else "was"
        self.has = "have" if p else "has"
        self.hasnt = "haven't" if p else "hasn't"
        self.does = "do" if p else "does"
        self.it = "they" if p else "it"
        self.them = "them" if p else "it"
        self.its = "their" if p else "its"
        self.its_short = "they're" if p else "it's"
        self.s = "" if p else "s"


def same_items(a: dict, b: dict) -> bool:
    return items_phrase(a["items"], brand=False) == items_phrase(
        b["items"], brand=False
    )


def order_name(order: dict, orders_: list[dict] | None = None) -> str:
    """'the running shoes and socks'; with the last four digits, said digit by digit,
    only when another order holds the same items."""
    name = f"the {items_phrase(order['items'], brand=False)}"
    if orders_ and any(
        o["order_number"] != order["order_number"] and same_items(o, order)
        for o in orders_
    ):
        name += f" ending {say_digits(last_four(order))}"
    return name


def short_items(order: dict) -> str:
    return items_phrase(order["items"], brand=False)


# --- The caller's orders and which one they mean -------------------------------


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


def _wanted_words(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return [
        w
        for w in words
        if w not in _STOP_WORDS and w not in _NUMBER_WORDS and w != "oh"
    ]


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
    wanted = {_stem(w) for w in _wanted_words(text)}
    if not wanted:
        return []
    scored = [(len(wanted & _order_words(o)), o) for o in orders_]
    best = max((s for s, _ in scored), default=0)
    return [o for s, o in scored if best and s == best]


def names_an_order(text: str) -> bool:
    """Whether a hint names anything (digits, or a word that isn't filler like 'my order' or
    'okay')."""
    words = set(re.findall(r"[a-z]+", (text or "").lower()))
    return bool(
        _digit_runs(text or "")
        or words - _STOP_WORDS - _CURRENT_WORDS - _ALL_WORDS - _ACKS
    )


def by_digits(text: str) -> bool:
    """The caller picked the order by digits of its number, not by an item."""
    return bool(_digit_runs(text or ""))


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


def listing(orders_: list[dict]) -> str:
    """The three most recent orders by item: 'the hoodie and water bottle, the cap, and the
    jacket', then 'and a couple of older ones' if there are more."""
    names = [order_name(o, orders_) for o in orders_[:MAX_ORDERS_LISTED]]
    if len(orders_) > MAX_ORDERS_LISTED:
        names.append("a couple of older ones")
    return _list(names)


def count_word(n: int) -> str:
    return _COUNT_WORDS[n] if n < len(_COUNT_WORDS) else str(n)


def call_again(task_tool: str) -> str:
    """The last sentence of every return that needs another answer from the caller, so the
    model passes the answer to the tool (Dialog-RSN-1 won't repeat a call on its own)."""
    return f"Then call {task_tool} again with whatever they say, even if it's the same as before."


def which_order_line(
    orders_: list[dict], question: str, matched: list[dict] | None = None
) -> str:
    """What the caller hears when the agent needs to know which order: none named yet, or a
    description that fits several."""
    if matched:
        names = [order_name(o, matched) for o in matched[:MAX_ORDERS_LISTED]]
        return f"Is it {_list(names, 'or')}?"
    many = count_word(len(orders_)) if len(orders_) <= MAX_ORDERS_LISTED else "a few"
    return f"I can see {many} recent orders: {listing(orders_)}. {question}"


def which_order_instruction(
    orders_: list[dict], conv, task_tool: str, question: str, matched=None
) -> str:
    line = which_order_line(orders_, question, matched)
    return (
        f'Ask which order, in these words: "{line}" Don\'t say order numbers. '
        f"{call_again(task_tool)}"
    )


def _missing_thing(hint: str) -> str:
    if by_digits(hint):
        return "that number"
    words = _wanted_words(hint)
    if not words:
        return "that"
    thing = " ".join(words)
    if thing.endswith("s"):
        return thing
    return ("an " if thing[0] in "aeiou" else "a ") + thing


def no_matching_order(
    orders_: list[dict], conv, task_tool: str, hint: str
) -> str | dict:
    """The caller described an order that isn't on the account: a miss, counted here. The
    attempt is named, and the last miss transfers."""
    misses = int(conv.state.order_misses or 0) + 1
    conv.state.order_misses = misses
    if misses >= MAX_ORDER_MISSES:
        conv.state.order_misses = 0
        conv.write_metric("ORDER_NOT_MATCHED")
        return handoff(conv, "ORDER_NOT_FOUND", NO_MATCH_LINE, "CUSTOMER_SERVICE")
    line = (
        f"I can't see an order with {_missing_thing(hint)} on your account. The ones I can see "
        f"are {listing(orders_)}. Is it one of those?"
    )
    return (
        f'NO MATCHING ORDER (attempt {misses} of {MAX_ORDER_MISSES}): say "{line}" '
        f"{call_again(task_tool)}"
    )


# --- Status ---------------------------------------------------------------------


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


def colleague_line(order: dict) -> str:
    return (
        f"I can see your {items_phrase(order['items'])} order, but it needs someone on the team "
        "to look at it. I'll put you through now. One moment, please."
    )


def _business_days_between(start: date, end: date) -> int:
    return sum(
        1
        for n in range(1, (end - start).days + 1)
        if (start + timedelta(n)).weekday() < 5
    )


def late_days(item: dict, conv) -> int | None:
    """Business days a shipped, undelivered item is past its expected date; None if it
    isn't late."""
    if item["status"] != api.SHIPPED or not item["expected_delivery"]:
        return None
    expected = date.fromisoformat(item["expected_delivery"][:10])
    now = today(conv)
    if expected >= now:
        return None
    return _business_days_between(expected, now)


def is_well_overdue(order: dict, conv) -> bool:
    return any((late_days(i, conv) or 0) > LATE_BUSINESS_DAYS for i in order["items"])


def is_late(order: dict, conv) -> bool:
    return any(late_days(i, conv) is not None for i in order["items"])


def _groups(order: dict, conv) -> list[tuple[str, list[dict]]]:
    """Items grouped by what the caller is told about them; cancelled items last."""
    groups: dict[tuple, list[dict]] = {}
    for item in order["items"]:
        key = (
            item["status"],
            item["carrier"],
            item["expected_delivery"],
            item["completed_on"],
            item["cancel_reason"],
        )
        groups.setdefault(key, []).append(item)
    out = [(key[0], items) for key, items in groups.items()]
    return sorted(out, key=lambda g: g[0] == api.CANCELLED)


def _city(item: dict) -> str:
    return (item["last_scan"] or "").split(",")[0].strip()


def _pickup_bring(conv) -> str:
    """The sentence of instore_pickup_info that says what to bring, if there is one."""
    info = store_info.attr(conv, "instore_pickup_info")
    for sentence in re.split(r"(?<=[.!?])\s+", info):
        if re.search(r"\bbring\b", sentence, re.I):
            sentence = sentence.strip()
            if sentence.lower().startswith("bring "):
                sentence = "Just bring " + sentence[6:]
            return sentence
    return ""


def _group_sentence(
    status: str, items: list[dict], order: dict, conv, split: bool
) -> str:
    w = _Words(items)
    first = items[0]
    if status == api.CANCELLED:
        names = items_phrase(items, brand=False)
        whole = len(items) == len(order["items"])
        if first["cancel_reason"] == "customer_request":
            if whole:
                return "That order was cancelled at your request, so you won't be charged for it."
            return (
                f"The {names} {w.was} cancelled at your request, so you won't be charged for "
                f"{w.them}."
            )
        lead = f"The {names} from that order" if split else f"The {names}"
        return (
            f"{lead} {w.was} out of stock, I'm afraid, so we cancelled {w.them}, and you won't be "
            f"charged for {w.them}."
        )
    names = items_phrase(items)
    if status == api.SHIPPED:
        late = late_days(first, conv)
        if late is not None:
            due = on_date(first["expected_delivery"], conv)
            if late > LATE_BUSINESS_DAYS:
                return (
                    f"Your {names} {w.was} due {due}, so {w.its_short} well overdue, I'm sorry. "
                    "The team can look into it with the carrier. Would you like me to put you "
                    "through?"
                )
            text = f"Your {names} {w.was} due {due}, so {w.its_short} running a little late, I'm sorry."
            if first["last_scan"]:
                when = (
                    f" {on_date(first['last_scan_on'], conv)}"
                    if first["last_scan_on"]
                    else ""
                )
                text += f" The last update was in {_city(first)}{when}."
            return text
        if first["expected_delivery"]:
            return (
                f"Your {names} {w.is_} on {w.its} way and should arrive "
                f"{on_date(first['expected_delivery'], conv)}."
            )
        carrier = f" with {first['carrier']}" if first["carrier"] else ""
        return (
            f"Your {names} {w.is_} on {w.its} way{carrier}, but I don't have a delivery date "
            f"for {w.them} yet."
        )
    if status == api.DELIVERED:
        when = (
            f" {on_date(first['completed_on'], conv)}" if first["completed_on"] else ""
        )
        return f"Your {names} {w.was} delivered{when}."
    if status == api.READY_FOR_PICKUP:
        return f"Your {names} {w.is_} ready to pick up in store. {_pickup_bring(conv)}".strip()
    if status == api.PICKED_UP:
        when = (
            f" {on_date(first['completed_on'], conv)}" if first["completed_on"] else ""
        )
        return f"Your {names} {w.was} picked up{when}."
    if order["fulfilment"] == "pickup":
        return (
            f"Your {names} {w.is_} still being prepared. We'll email you as soon as {w.its_short} "
            "ready to pick up in store."
        )
    return (
        f"Your {names} {w.is_} still being prepared, so {w.it} {w.hasnt} shipped yet. We'll "
        f"email you a tracking link as soon as {w.it} {w.does}."
    )


def say_status(order: dict, conv) -> str:
    """What to tell the caller about one order: one sentence per status group, the shipped
    part first."""
    groups = _groups(order, conv)
    split = len(groups) > 1
    return " ".join(
        _group_sentence(s, items, order, conv, split) for s, items in groups
    )


def status_details(order: dict, conv) -> str:
    """Details to give only if asked: carrier, last scan, ship date, delivery address, and
    the pickup policy."""
    parts = []
    for status, items in _groups(order, conv):
        first = items[0]
        names = items_phrase(items, brand=False)
        bits = []
        if first["carrier"]:
            bits.append(f"carrier {first['carrier']}")
        if first["last_scan"]:
            when = (
                f" {on_date(first['last_scan_on'], conv)}"
                if first["last_scan_on"]
                else ""
            )
            bits.append(f"last scanned in {first['last_scan']}{when}")
        if first["shipped_on"]:
            bits.append(f"shipped {on_date(first['shipped_on'], conv)}")
        if first["expected_delivery"] and status == api.SHIPPED:
            bits.append(f"expected {on_date(first['expected_delivery'], conv)}")
        if bits:
            parts.append(f"{names}: " + ", ".join(bits))
    if order["fulfilment"] == "pickup":
        info = store_info.attr(conv, "instore_pickup_info")
        if info:
            parts.append(f"pickup: {info}")
    elif order["shipping_address"]:
        parts.append(f"being delivered to {order['shipping_address']}")
    return "; ".join(parts)


def short_status(order: dict, conv) -> str:
    """One short clause for an order in a summary of several: 'your Adidas backpack hasn't
    shipped yet'."""
    if needs_colleague(order):
        return f"your {items_phrase(order['items'])} order needs someone on the team to look at it"
    groups = _groups(order, conv)
    status, items = groups[0]
    w = _Words(items)
    names = items_phrase(items)
    first = items[0]
    if status == api.CANCELLED:
        return f"your {items_phrase(order['items'])} order was cancelled"
    if status == api.SHIPPED:
        late = late_days(first, conv)
        if late is not None:
            due = on_date(first["expected_delivery"], conv)
            return f"your {names} {w.was} due {due}, so {w.its_short} running late"
        if first["expected_delivery"]:
            return (
                f"your {names} {w.is_} on {w.its} way and should arrive "
                f"{on_date(first['expected_delivery'], conv)}"
            )
        return f"your {names} {w.is_} on {w.its} way"
    if status == api.DELIVERED:
        when = (
            f" {on_date(first['completed_on'], conv)}" if first["completed_on"] else ""
        )
        return f"your {names} {w.was} delivered{when}"
    if status == api.READY_FOR_PICKUP:
        return f"your {names} {w.is_} ready to pick up in store"
    if status == api.PICKED_UP:
        return f"your {names} {w.was} picked up"
    if order["fulfilment"] == "pickup":
        return f"your {names} {w.is_} still being prepared"
    return f"your {names} {w.hasnt} shipped yet"


def summary_line(orders_: list[dict], conv) -> str:
    """Two orders: one sentence. Three: a sentence each."""
    shown = sorted(
        orders_[:MAX_ORDERS_LISTED], key=lambda o: not in_transit(o)
    )  # shipped first
    clauses = [short_status(o, conv) for o in shown]
    if len(clauses) == 2:
        text = f"{clauses[0]}, and {clauses[1]}."
        return text[0].upper() + text[1:]
    return " ".join(c[0].upper() + c[1:] + "." for c in clauses)


def not_received_line(order: dict, conv) -> str:
    """Delivered, but the caller hasn't got it: the one question before a transfer."""
    delivered = [i for i in order["items"] if i["status"] == api.DELIVERED]
    if not delivered:
        return ""
    w = _Words(delivered)
    when = (
        f" {on_date(delivered[0]['completed_on'], conv)}"
        if delivered[0]["completed_on"]
        else ""
    )
    return (
        f"I'm sorry about that. {w.it.capitalize()} show{w.s} as delivered{when}. Sometimes "
        "parcels are left with a neighbor or somewhere safe nearby. Have you had a chance to check?"
    )


def tracking_url(order: dict) -> str:
    return next(
        (
            i["tracking_url"]
            for i in order["items"]
            if i["status"] in (api.SHIPPED, api.DELIVERED) and i["tracking_url"]
        ),
        "",
    )


def in_transit(order: dict) -> bool:
    return any(i["status"] == api.SHIPPED for i in order["items"])


# --- What can change -------------------------------------------------------------


def items_with(order: dict, statuses: tuple) -> list[dict]:
    return [i for i in order["items"] if i["status"] in statuses]


def cancel_block(order: dict) -> str:
    """Why this order can't be cancelled here, as the caller hears it, or '' if it can."""
    if all(i["status"] == api.CANCELLED for i in order["items"]):
        return "That order's already been cancelled, so there's nothing more you need to do."
    moving = items_with(order, (api.SHIPPED,))
    done = items_with(order, (api.DELIVERED, api.PICKED_UP))
    if moving or done:
        items = moving or done
        w = _Words(items)
        lead = (
            f"Your {items_phrase(items)} {w.has} already shipped"
            if moving
            else f"Your {items_phrase(items)} {w.has} already been delivered"
        )
        after = (
            f"Once {w.it} arrive{'' if w.it == 'they' else 's'}, you"
            if moving
            else "You"
        )
        return (
            f"{lead}, so I'm afraid I can't cancel {w.them} now. {after} can return {w.them} in "
            "any store or through our returns portal."
        )
    ready = items_with(order, (api.READY_FOR_PICKUP,))
    if ready:
        w = _Words(ready)
        waiting = "are" if w.it == "they" else "'s"
        sep = " " if waiting == "are" else ""
        return (
            f"Your {items_phrase(ready, brand=False)}{sep}{waiting} already waiting for you in "
            f"store, so I can't cancel {w.them} from here. If you don't want {w.them}, you can "
            "just not collect it, or I can put you through to the team to cancel it."
        )
    return ""


def address_block(order: dict) -> str:
    """Why this order's delivery address can't be changed, as the caller hears it, or ''."""
    if order["fulfilment"] == "pickup":
        return "That's a pickup order, so it'll be waiting for you in store rather than delivered."
    if all(i["status"] == api.CANCELLED for i in order["items"]):
        return "That order's been cancelled, so there's nothing on its way."
    moving = items_with(order, (api.SHIPPED,))
    if moving:
        w = _Words(moving)
        carrier = moving[0]["carrier"]
        page = (
            f"the {carrier} tracking page" if carrier else "the carrier's tracking page"
        )
        return (
            f"Your {items_phrase(moving, brand=False)} {w.has} already shipped, so I can't change "
            f"the address from here, I'm afraid. You might be able to redirect {w.them} on {page}."
        )
    done = items_with(order, (api.DELIVERED, api.PICKED_UP))
    if done:
        w = _Words(done)
        return (
            f"Your {items_phrase(done, brand=False)} {w.has} already been delivered, so I can't "
            "change the address now."
        )
    return ""


# --- Readbacks ---------------------------------------------------------------------


def readback_text(
    conv, key: str, fields: list[tuple[str, str]]
) -> tuple[list[str], str]:
    """What to read back for `key`: every field the first time, then only the fields whose
    value changed since the last readback.

    Returns (labels, mode): mode is "full" the first time, "changes" when some fields
    changed, and "none" when the caller has already heard all of it.
    """
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    last = store.get(key)
    current = {label: value for label, value in fields if value}
    conv.state.readbacks = {**store, key: current}
    if last is None:
        return list(current), "full"
    changed = [label for label, value in current.items() if last.get(label) != value]
    changed += [label for label in last if label not in current]
    return changed, ("changes" if changed else "none")


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


def asked(conv, key: str, question: str = "") -> None:
    """Record the turn in which a write's readback asked its question, and the question,
    so a same-turn call can speak it again."""
    turns = (
        dict(conv.state.readback_turns)
        if isinstance(conv.state.readback_turns, dict)
        else {}
    )
    turns[key] = _turn(conv)
    conv.state.readback_turns = turns
    if question:
        said = (
            dict(conv.state.readback_said)
            if isinstance(conv.state.readback_said, dict)
            else {}
        )
        said[key] = question
        conv.state.readback_said = said


def last_question(conv, key: str) -> str:
    said = (
        conv.state.readback_said if isinstance(conv.state.readback_said, dict) else {}
    )
    return said.get(key, "")


def same_turn_as_ask(conv, key: str) -> bool:
    """True while the caller can't have answered the readback yet (same turn)."""
    turns = (
        conv.state.readback_turns if isinstance(conv.state.readback_turns, dict) else {}
    )
    turn = _turn(conv)
    return turn is not None and key in turns and turns.get(key) == turn


def wait_for_answer(conv, key: str) -> dict:
    """The same-turn refusal: nothing is written, and the readback and its question are
    spoken again as the utterance, which ends the turn (on RSN-1 a same-turn utterance
    replaces the model's turn, so code builds it)."""
    return {"utterance": last_question(conv, key)}


YES_LINE = (
    'A yes, or an acknowledgement in answer to it ("okay", "sure", "sounds good", "go on"), is '
    "agreement"
)


# --- Call state ---------------------------------------------------------------------


def call_state(conv, task_lines: list[str], next_line: str) -> str:
    order = selected_order(conv)
    lines = [
        "CALL STATE (this replaces any earlier copy; never read it aloud)",
        f"- {idnv.state_line(conv)}",
        "- Order: " + (f"{order_name(order)} order" if order else "none chosen yet"),
    ]
    lines += [f"- {line}" for line in task_lines if line]
    lines.append(f"NEXT: {next_line}")
    return "\n".join(lines)
