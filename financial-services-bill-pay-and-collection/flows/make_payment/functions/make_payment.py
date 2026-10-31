from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.billing as billing
import functions.idnv as idnv
from flows.make_payment.functions.update_payment import (
    READBACK_KEY,
    ask_to_confirm,
    payment,
    payment_fields,
    payment_state,
    say_when,
)
from functions.handoff import transfer


@func_description(
    "Take the payment you read back, once the caller has said yes to it. If anything changed since the caller last heard the details, this reads back only the change first."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question the payment readback asked. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Okay, processing that payment now.", 3), ("Just a moment.", 3)],
)
def make_payment(conv: Conversation, flow: Flow, caller_confirmed: str):
    if not idnv.is_verified(conv, idnv.STRICT):
        return billing.gate(conv, "make_payment")
    p = payment(conv)
    if p["paid"]:
        return "This payment has already been made; don't take it again. Ask if there's anything else."
    if not p["amount"] or not p["method"]:
        return f"Not ready to pay: call update_payment.\n\n{payment_state(conv)}"

    acct = billing.verified_account(conv)
    problem = billing.amount_problem(p["amount"], acct["balance"])
    if problem:
        p["amount"] = None
        conv.state.payment = p
        return f"{problem}\n\n{payment_state(conv)}"

    fields = payment_fields(conv, p)
    if not billing.readback_is_current(conv, READBACK_KEY, fields):
        changed = billing.changed_fields(conv, READBACK_KEY, fields)
        billing.readback_text(conv, READBACK_KEY, fields)
        billing.mark_asked(conv, READBACK_KEY)
        return f"{ask_to_confirm(conv, p, changed)}\n\n{payment_state(conv)}"
    if str(caller_confirmed).strip().lower() != "true":
        billing.mark_asked(conv, READBACK_KEY)
        return (
            f"NOT PAID: the caller hasn't said a clear yes. {ask_to_confirm(conv, p, [])}"
            f"\n\n{payment_state(conv)}"
        )
    if billing.same_turn_as_question(conv, READBACK_KEY):
        return f"{billing.NOT_DONE_YET}\n\n{payment_state(conv)}"

    try:
        result = api_client.make_payment(
            conv, acct["id"], p["amount"], p["method"], p["date"]
        )
    except Exception:
        conv.log.error("make_payment failed", exc_info=True)
        return transfer(
            conv,
            "PAYMENT_FAILED",
            "I'm sorry, that payment didn't go through. Let me put you through to our payments "
            "team, one moment please.",
        )

    p["paid"] = result["confirmation_number"]
    conv.state.payment = p
    summary = f"payment of {billing.say_money(p['amount'])} {say_when(conv, p['date'])}"
    billing.record_transaction(conv, summary, result["confirmation_number"])
    billing.forget_readback(conv, READBACK_KEY)
    conv.write_metric(
        "PAYMENT_SUCCESSFUL",
        "today" if say_when(conv, p["date"]) == "today" else "scheduled",
    )
    conv.exit_flow()
    after = (
        f"their balance is now {billing.say_money(result['new_balance'])}"
        if p["date"] == billing.today(conv).isoformat()
        else f"their balance will be {billing.say_money(result['new_balance'])} once it goes out"
    )
    return (
        f"Done. Tell the caller the {summary} is confirmed, their confirmation number is "
        f"{billing.say_digits(result['confirmation_number'])}, and {after}. Don't repeat the "
        "other details. If they ask for the confirmation by text, call start_send_sms with "
        "sms_id 'payment_confirmation'. Then ask if there's anything else."
    )
