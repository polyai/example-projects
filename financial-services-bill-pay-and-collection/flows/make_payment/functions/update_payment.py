from _gen import *  # <AUTO GENERATED>
from functions import billing, idnv

READBACK_KEY = "payment"


def fresh_payment(conv) -> dict:
    acct = billing.account(conv) or {}
    methods = acct.get("payment_methods") or []
    return {
        "amount": None,
        "method": methods[0] if methods else "",
        "date": billing.today(conv).isoformat(),
        "paid": "",
    }


def payment(conv) -> dict:
    p = conv.state.payment
    return dict(p) if isinstance(p, dict) else fresh_payment(conv)


def say_when(conv, iso: str) -> str:
    return (
        "today"
        if iso == billing.today(conv).isoformat()
        else f"on {billing.say_date(iso)}"
    )


def payment_fields(conv, p: dict) -> list[tuple[str, str]]:
    if not (p["amount"] and p["method"]):
        return []
    return [
        ("amount", billing.say_money(p["amount"])),
        ("method", f"from your {p['method']}"),
        ("when", say_when(conv, p["date"])),
    ]


def payment_question(conv, p: dict, changed: list[str] | None = None) -> str:
    """The yes-or-no question that is also the readback, kept short for voice: the action and
    the amount always; the card and day the first time (changed=None), then only what changed
    ("Shall I pay $50.00 on Friday, October 30th instead, yes or no?"). An empty list (asking
    again after an unclear answer) names the amount only."""
    fields = dict(payment_fields(conv, p))
    parts = [f"pay {fields['amount']}"]
    if changed is None:
        parts += [fields["method"], fields["when"]]
    else:
        parts += [fields[k] for k in ("method", "when") if k in changed]
        if changed:
            parts.append("instead")
    return f"Shall I {' '.join(parts)}, yes or no?"


def ask_to_confirm(conv, p: dict, changed: list[str] | None = None) -> str:
    """The caller hears the readback and the yes-or-no question as one sentence that names the
    action, so an "okay" doesn't answer it."""
    return (
        f'Ask the caller, in these words: "{payment_question(conv, p, changed)}" Then wait for '
        "their answer."
    )


def payment_state(conv) -> str:
    p = payment(conv)
    acct = billing.account(conv) or {}
    lines = [
        "Task: make a payment",
        f"Balance: {billing.say_money(acct.get('balance', 0))}",
        f"Payment methods on file: {', '.join(acct.get('payment_methods') or []) or 'none'}",
        "Amount: " + (billing.say_money(p["amount"]) if p["amount"] else "not given"),
        "Pay with: " + (p["method"] or "not chosen"),
        "When: " + say_when(conv, p["date"]),
    ]
    if not p["amount"]:
        nxt = "Ask how much they'd like to pay."
    elif not p["method"]:
        nxt = "Ask which payment method on file to use."
    else:
        nxt = "Wait for a clear yes or no to the payment question, or a change."
    return billing.call_state(conv, lines, nxt)


@func_description(
    "Save the payment the caller wants to make and get the readback once the amount is known. Call it whenever they give or change the amount, the card or account to pay with, or the date."
)
@func_parameter(
    "amount",
    "The amount the caller said, in dollars as a number, e.g. '50' or '125.40'. Pass it as they said it, even if it's more than the balance or the phone limit: this tool checks it.",
)
@func_parameter(
    "payment_method",
    "Which card or bank account on file to pay with, in their words, e.g. 'the Visa'. Empty if not said.",
)
@func_parameter(
    "pay_date",
    "When the payment should go out: 'today' or a date as YYYY-MM-DD. Empty if not said.",
)
def update_payment(
    conv: Conversation, flow: Flow, amount: str, payment_method: str, pay_date: str
):
    if not idnv.is_verified(conv, idnv.STRICT):
        return billing.gate(conv, "make_payment")
    p = payment(conv)
    if p["paid"]:
        return "This payment has already been made; don't take it again. Ask if there's anything else."
    acct = billing.verified_account(conv)
    notes = []

    if str(payment_method or "").strip():
        matched = billing.match_method(payment_method, acct["payment_methods"])
        if matched:
            p["method"] = matched
        else:
            notes.append(
                f"'{payment_method}' isn't on file (on file: {', '.join(acct['payment_methods'])}). "
                "Tell the caller you can only use a payment method on file; a new card can be "
                "added online or in the app, or our payments team can take the card details "
                "securely (if they want that, call handoff with handoff_reason='CARD_PAYMENT')."
            )

    if str(pay_date or "").strip():
        when, problem = billing.date_problem(conv, pay_date)
        if problem:
            notes.append(problem)
        else:
            p["date"] = when

    if str(amount or "").strip():
        value = billing.parse_amount(amount)
        problem = billing.amount_problem(value, acct["balance"])
        if problem:
            p["amount"] = None
            notes.append(problem)
        else:
            p["amount"] = value
    conv.state.payment = p

    if notes:
        return " ".join(notes) + f"\n\n{payment_state(conv)}"
    if not p["amount"]:
        return f"Ask how much they'd like to pay.\n\n{payment_state(conv)}"
    if not p["method"]:
        return f"Ask which payment method on file to use.\n\n{payment_state(conv)}"

    fields = payment_fields(conv, p)
    changed = billing.changed_fields(conv, READBACK_KEY, fields)
    _, mode = billing.readback_text(conv, READBACK_KEY, fields)
    if mode == "none":
        return (
            "Nothing has changed since the caller heard it; don't read it again. If their latest "
            "reply was a clear yes to the payment question, call make_payment with "
            "caller_confirmed='true'; otherwise ask the yes-or-no question again."
            f"\n\n{payment_state(conv)}"
        )
    billing.mark_asked(conv, READBACK_KEY)
    return f"{ask_to_confirm(conv, p, changed)}\n\n{payment_state(conv)}"
