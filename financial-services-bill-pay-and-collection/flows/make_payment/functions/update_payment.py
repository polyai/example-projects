from _gen import *  # <AUTO GENERATED>
from functions import billing, idnv, payments


@func_description(
    "Save the payment the caller wants to make and get the readback. Call it whenever they give or change the amount, the card or account to pay with, or the day. It checks every rule and says what to ask, offer or read back next."
)
@func_parameter(
    "amount",
    "The amount the caller said, e.g. '50', '125.40', or 'all' for all of it, the full amount or paying it off. Pass it as they said it, even if it's over the balance or a limit: this tool checks it.",
)
@func_parameter(
    "payment_method",
    "The card or bank account the caller named to pay with, in their words, e.g. 'the Visa' or 'the checking account'. Leave it out unless the caller named one: never choose for them. Never the digits of a card that isn't on file.",
)
@func_parameter(
    "pay_date",
    "When the payment should go out: 'today' or a date as YYYY-MM-DD from the date list.",
)
@func_parameter(
    "day_said",
    "The caller's own words for the day, e.g. 'this Friday' or 'the 20th of December'.",
)
def update_payment(
    conv: Conversation,
    flow: Flow,
    amount: str,
    payment_method: str,
    pay_date: str,
    day_said: str,
):
    if not idnv.is_verified(conv, idnv.STRICT):
        return billing.gate(conv, "make_payment")
    p = payments.payment(conv)
    if p["paid"]:
        return (
            "This payment has already gone through; don't take it again. If they want another "
            "payment, call start_make_payment. Otherwise ask if there's anything else."
        )
    acct = billing.verified_account(conv)
    methods = acct.get("payment_methods") or []
    asks = []

    if str(payment_method or "").strip():
        matched = billing.match_method(payment_method, methods)
        if matched:
            p["method"] = matched
        elif matched == "":
            asks.append(payments.NOT_ON_FILE)

    if str(pay_date or "").strip() or str(day_said or "").strip():
        when, problem = billing.date_problem(conv, pay_date, day_said)
        if problem:
            asks.append(problem)
        else:
            p["date"] = when

    if str(amount or "").strip():
        value = billing.parse_amount(amount)
        if value == billing.ALL:
            value = round(float(acct.get("balance", 0)), 2)
        problem = payments.amount_problem(conv, value, acct)
        if problem:
            p["amount"] = None
            asks.append(problem)
        else:
            p["amount"] = value
    payments.save(conv, p)

    if asks:
        return f"{asks[0]}\n\n{payments.state_block(conv)}"
    if not p["amount"]:
        return f"{payments.amount_problem(conv, None, acct)}\n\n{payments.state_block(conv)}"
    if not p["method"]:
        if not methods:
            return f"{payments.NOT_ON_FILE}\n\n{payments.state_block(conv)}"
        return f"{payments.method_question(methods)}\n\n{payments.state_block(conv)}"

    if payments.is_current(conv, p):
        return (
            "Nothing has changed since the caller heard the readback; don't read it again. If "
            "their latest reply agreed to it, call make_payment with caller_confirmed='true'; "
            f'otherwise ask: "{payments.QUESTION}"\n\n{payments.state_block(conv)}'
        )
    return f"{payments.ask_to_confirm(conv, p, acct)}\n\n{payments.state_block(conv)}"
