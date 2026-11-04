"""The payment being set up on this call: its state, its rules and its readback.

update_payment and make_payment (flows/make_payment/functions/) and the verify_caller resume
all read and write it through here, so tools only import from functions/.

What the caller hears (design 2.3):
- the readback, one sentence then the question: "So that's $50 from your Visa ending four two
  four two, going out today. Shall I make that payment?";
- after a change, only what changed: "So that's $75 instead. Shall I make that payment?";
- once per payment, a note when the date is after the due date, or when this payment plus the
  scheduled ones is more than the balance.
"""

from _gen import *  # <AUTO GENERATED>
from functions import billing

READBACK_KEY = "payment"
QUESTION = "Shall I make that payment?"
ASK_AFTER_WAIT = "Great. Shall I make that payment, then?"
LATE_NOTE = "Just so you know, that's after your due date, so a late fee may apply."


@func_description("[UTIL] The payment on this call, not callable directly")
def payments(conv: Conversation):
    return "Payment helpers module."


def fresh_payment(conv) -> dict:
    """A new payment: today, and the method on file only when there's exactly one."""
    acct = billing.account(conv) or {}
    methods = acct.get("payment_methods") or []
    made = int(conv.state.payments_made or 0)
    return {
        "amount": None,
        "method": methods[0] if len(methods) == 1 else "",
        "date": billing.today(conv).isoformat(),
        "paid": "",
        "pending": False,
        "notes_said": [],
        "another": made > 0,
    }


def payment(conv) -> dict:
    p = conv.state.payment
    return dict(p) if isinstance(p, dict) else fresh_payment(conv)


def save(conv, p: dict) -> None:
    conv.state.payment = p


def clear(conv) -> None:
    """Drop an unpaid payment (a fraud handoff, a new task): nothing is written after it."""
    p = conv.state.payment
    if isinstance(p, dict) and not p.get("paid"):
        conv.state.payment = None
        billing.forget_asked(conv, READBACK_KEY)
        store = (
            dict(conv.state.readbacks) if isinstance(conv.state.readbacks, dict) else {}
        )
        store.pop(READBACK_KEY, None)
        conv.state.readbacks = store


def say_when(conv, iso: str) -> str:
    return billing.say_on(conv, iso)


def fields(conv, p: dict) -> dict:
    """The readback's fields, as said."""
    if not (p.get("amount") and p.get("method")):
        return {}
    return {
        "amount": billing.say_money(p["amount"]),
        "method": f"from your {billing.say_method(p['method'])}",
        "when": f"going out {say_when(conv, p['date'])}",
    }


def _heard(conv) -> dict | None:
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    return store.get(READBACK_KEY)


def _remember(conv, current: dict) -> None:
    store = dict(conv.state.readbacks) if isinstance(conv.state.readbacks, dict) else {}
    store[READBACK_KEY] = current
    conv.state.readbacks = store


def is_current(conv, p: dict) -> bool:
    """The caller has heard exactly what would be paid."""
    current = fields(conv, p)
    return bool(current) and _heard(conv) == current


def notes(conv, p: dict, acct: dict) -> list[tuple[str, str]]:
    """(key, sentence) for each one-off note that applies to this payment."""
    out = []
    due = acct.get("due_date") or ""
    if due and p["date"] > due:
        out.append(("late", LATE_NOTE))
    scheduled = acct.get("scheduled_payments") or []
    if scheduled and p["amount"] + sum(s["amount"] for s in scheduled) > acct.get(
        "balance", 0
    ):
        items = " and ".join(
            f"{billing.say_money(s['amount'])} set to go out on {billing.say_the(s['date'])}"
            for s in scheduled
        )
        out.append(("scheduled", f"Just so you know, you've also got {items}."))
    return out


def readback(conv, p: dict, acct: dict) -> str:
    """The readback sentence, any new notes, then the question. Remembers what was said, so
    the next readback names only what changed."""
    current = fields(conv, p)
    last = _heard(conv)
    if last is None:
        another = "another " if p.get("another") else ""
        text = f"So that's {another}{current['amount']} {current['method']}, {current['when']}."
    else:
        changed = [k for k in ("amount", "method", "when") if last.get(k) != current[k]]
        if changed:
            head = " ".join(current[k] for k in ("amount", "method") if k in changed)
            if "when" in changed:
                head = f"{head}, {current['when']}" if head else current["when"]
            text = f"So that's {head} instead."
        else:
            text = ""
    said = list(p.get("notes_said") or [])
    for key, sentence in notes(conv, p, acct):
        if key not in said:
            text += f" {sentence}"
            said.append(key)
    p["notes_said"] = said
    p["waited"] = False
    save(conv, p)
    _remember(conv, current)
    billing.mark_asked(conv, READBACK_KEY)
    return f"{text} {QUESTION}".strip()


def _opener(conv) -> str:
    """The ID&V thanks, when the readback comes in the same turn the caller was confirmed."""
    kept = (
        conv.state.verified_opener
        if isinstance(conv.state.verified_opener, dict)
        else {}
    )
    if (
        kept.get("line")
        and kept.get("turn") is not None
        and kept["turn"] == billing.history_turn(conv)
    ):
        return kept["line"] + " "
    return ""


def ask_to_confirm(conv, p: dict, acct: dict) -> str:
    return (
        f'Say, in these words: "{_opener(conv)}{readback(conv, p, acct)}" Then wait for their answer. A yes, or '
        'an acknowledgement ("okay", "sure", "go ahead"), to that question → call make_payment '
        "with caller_confirmed='true'. A change → call update_payment with it."
    )


def method_question(methods: list[str]) -> str:
    if len(methods) == 2:
        a, b = (billing.say_method(m) for m in methods)
        return f'Ask: "Would you like to pay with your {a}, or your {b}?"'
    named = "; ".join(billing.say_method(m) for m in methods)
    return f'Ask: "Which card or account would you like to use?" Name them only if they ask: {named}.'


NOT_ON_FILE = (
    "Say, in these words: \"I can only use a card or account that's already on your account. "
    "You can add a new one in the app or online, or our payments team can take the details "
    'securely. Would you like me to put you through?" If they were reading out a card number, '
    'start with: "Sorry to stop you, but please don\'t read your card number out to me." A yes '
    "→ call handoff with handoff_reason=CARD_PAYMENT. Or they can choose a card or account "
    "that's on file."
)


def amount_problem(conv, amount, acct: dict) -> str:
    """Why this amount can't be taken, with the offer to make; '' if it can. The balance is
    checked before the phone limit, so a caller who says $5,000 on a $150 balance hears about
    the balance."""
    balance = round(float(acct.get("balance", 0)), 2)
    if balance <= 0:
        return (
            f'Say: "{billing.balance_sentence(conv, acct)} So there\'s nothing to pay right now." '
            "Then ask if there's anything else."
        )
    limit = billing.MAX_PHONE_PAYMENT
    if amount is None or amount <= 0:
        return 'Ask: "How much would you like to pay?"'
    limit_offer = (
        f'Say: "The most I can take over the phone is {billing.say_money(limit)}. Would you like '
        f'to pay {billing.say_money(limit)} now, or shall I put you through to our payments team?" '
        f"Paying {billing.say_money(limit)} → call update_payment with amount {limit:.0f}. The "
        "payments team → call handoff with handoff_reason=PAYMENT_OVER_PHONE_LIMIT."
    )
    if amount > balance:
        if balance > limit:
            return limit_offer
        return (
            f"Say: \"Your balance is {billing.say_money(balance)}, so I can't take more than "
            f'that. Would you like to pay the full {billing.say_money(balance)}?" A yes sets the '
            f"amount: call update_payment with amount {balance:g}. It isn't the payment's yes."
        )
    if amount > limit:
        return limit_offer
    return ""


def entry_instruction(conv, opener: str = "") -> str:
    """The first thing said in the payment flow, once the caller is verified."""
    acct = billing.verified_account(conv)
    if not isinstance(conv.state.payment, dict) or conv.state.payment.get("paid"):
        save(conv, fresh_payment(conv))
    balance = (
        ""
        if conv.state.balance_heard
        else billing.balance_sentence(conv, acct, short=True)
    )
    conv.state.balance_heard = True
    if acct.get("balance", 0) <= 0:
        said = f"{opener} {balance} So there's nothing to pay right now.".strip()
        return f'Say: "{said}" Then ask if there\'s anything else.'
    if opener:
        conv.state.verified_opener = {
            "line": opener,
            "turn": billing.history_turn(conv),
        }
    said = f"{opener} {balance} How much would you like to pay?".strip()
    first = "say "
    return (
        "Help the caller make a payment. If they have already said how much ('all of it', 'the "
        "whole thing' and 'pay it off' count: pass amount 'all'), or which card or day, call "
        f"update_payment with it now, before you reply, and {first}what it returns. "
        f'Otherwise say: "{said}"'
    )


def state_block(conv) -> str:
    p = payment(conv)
    acct = billing.account(conv) or {}
    lines = [
        "Task: make a payment",
        f"Balance: {billing.say_money(acct.get('balance', 0))}",
        "Methods on file: "
        + (
            ", ".join(billing.say_method(m) for m in acct.get("payment_methods") or [])
            or "none"
        ),
        "Amount: " + (billing.say_money(p["amount"]) if p["amount"] else "not given"),
        "Pay with: "
        + (billing.say_method(p["method"]) if p["method"] else "not chosen"),
        "When: " + say_when(conv, p["date"]),
    ]
    if not p["amount"]:
        nxt = "Ask how much they'd like to pay."
    elif not p["method"]:
        nxt = "Ask which card or account on file to use."
    else:
        nxt = f'Wait for their answer to "{QUESTION}", or a change.'
    return billing.call_state(conv, lines, nxt)
