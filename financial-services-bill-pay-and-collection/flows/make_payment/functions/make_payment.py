from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.billing as billing
import functions.idnv as idnv
import functions.payments as payments
from functions.handoff import transfer

FAILED_LINE = (
    "I'm sorry, I couldn't confirm that payment. I'll put you through to our payments team so "
    "they can check it for you. One moment, please."
)


def done_line(conv, p: dict, result: dict) -> str:
    """What the caller hears once the payment is made (design 2.3)."""
    amount = billing.say_money(p["amount"])
    number = billing.say_digits(result["confirmation_number"])
    if p["date"] == billing.today(conv).isoformat():
        return (
            f"That's all gone through. I've paid {amount} from your "
            f"{billing.short_method(p['method'])}, and your balance is now "
            f"{billing.say_money(result['new_balance'])}. Your confirmation number is {number}. "
            "Is there anything else I can help with?"
        )
    return (
        f"That's all set. Your {amount} payment will go out {payments.say_when(conv, p['date'])}, "
        f"and your confirmation number is {number}. Is there anything else I can help with?"
    )


@func_description(
    "Take the payment you read back, once the caller has agreed to it. If anything changed since the caller last heard the details, this reads back only the change first."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply agreed to the readback question this tool or update_payment returned (\"Shall I make that payment?\"). 'Okay', 'sure', 'go ahead' or 'sounds good' to that question is agreement; an answer to something else, or real hesitation ('hmm', 'let me check', a question back), is not: pass 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[
        ("Just a moment while I put that through.", 3),
        ("Nearly there.", 3),
    ],
)
def make_payment(conv: Conversation, flow: Flow, caller_confirmed: str):
    if not idnv.is_verified(conv, idnv.STRICT):
        return billing.gate(conv, "make_payment")
    p = payments.payment(conv)
    if p.get("pending"):
        # The last attempt's outcome is unknown: never try it again.
        return transfer(conv, "PAYMENT_FAILED", FAILED_LINE)
    if p["paid"]:
        return (
            "This payment has already gone through; don't take it again. If they want another "
            "payment, call start_make_payment. Otherwise ask if there's anything else."
        )
    if not p["amount"] or not p["method"]:
        return f"Not ready to pay: call update_payment.\n\n{payments.state_block(conv)}"

    acct = billing.verified_account(conv)
    problem = payments.amount_problem(conv, p["amount"], acct)
    if problem:
        p["amount"] = None
        payments.save(conv, p)
        return f"{problem}\n\n{payments.state_block(conv)}"

    if not payments.is_current(conv, p):
        return (
            f"{payments.ask_to_confirm(conv, p, acct)}\n\n{payments.state_block(conv)}"
        )
    if str(caller_confirmed).strip().lower() != "true":
        billing.mark_asked(conv, payments.READBACK_KEY)
        return (
            "NOT PAID. If they asked something, answer it in a sentence or two, then ask: "
            f'"{payments.QUESTION}" If they need a moment, call user_needs_time. If they said no, '
            'say: "No '
            "problem, I haven't taken anything. Would you like to change the amount or the date, "
            f'or leave it for now?"\n\n{payments.state_block(conv)}'
        )
    if p.get("waited"):
        # The caller asked for a moment after the readback: what they said next answered the
        # wait, not the question. Ask it again before anything is paid.
        p["waited"] = False
        payments.save(conv, p)
        billing.mark_asked(conv, payments.READBACK_KEY)
        return {"utterance": payments.ASK_AFTER_WAIT}
    if billing.same_turn_as_question(conv, payments.READBACK_KEY):
        refusals = int(conv.state.same_turn_refusals or 0) + 1
        conv.state.same_turn_refusals = refusals
        if refusals > 1:
            # RSN-1 can keep calling in the turn it read back: speak the question and end the turn.
            return {"utterance": payments.QUESTION}
        return f"{billing.NOT_DONE_YET}\n\n{payments.state_block(conv)}"
    conv.state.same_turn_refusals = 0

    p["pending"] = True
    payments.save(conv, p)
    try:
        result = api_client.make_payment(
            conv, acct["id"], p["amount"], p["method"], p["date"]
        )
    except api_client.PaymentDeclined:
        p["pending"] = False
        payments.save(conv, p)
        billing.forget_asked(conv, payments.READBACK_KEY)
        others = [m for m in acct.get("payment_methods") or [] if m != p["method"]]
        offer = (
            f" Would you like to try your {billing.short_method(others[0])} instead?"
            if len(others) == 1
            else (" Would you like to use another card or account?" if others else "")
        )
        conv.write_metric("PAYMENT_DECLINED")
        return (
            f'NOT PAID. Say: "I\'m sorry, that payment was declined.{offer}" A different method '
            "on file → call update_payment with it. Only offer cards or accounts on file."
        )
    except Exception:
        # Expected on an outage; the caller goes to the payments team and nothing is retried.
        conv.log.warning("make_payment: billing API did not confirm the payment")
        conv.write_metric("PAYMENT_FAILED")
        return transfer(conv, "PAYMENT_FAILED", FAILED_LINE)

    p.update(paid=result["confirmation_number"], pending=False)
    payments.save(conv, p)
    conv.state.payments_made = int(conv.state.payments_made or 0) + 1
    summary = (
        f"{billing.say_money(p['amount'])} payment {payments.say_when(conv, p['date'])}"
    )
    billing.record_transaction(conv, summary, result["confirmation_number"])
    conv.state.last_confirmation_spoken = billing.say_digits(
        result["confirmation_number"]
    )
    billing.forget_asked(conv, payments.READBACK_KEY)
    store = dict(conv.state.readbacks) if isinstance(conv.state.readbacks, dict) else {}
    store.pop(payments.READBACK_KEY, None)
    conv.state.readbacks = store
    today = p["date"] == billing.today(conv).isoformat()
    conv.write_metric("PAYMENT_SUCCESSFUL", "today" if today else "scheduled")
    conv.exit_flow()
    line = done_line(conv, p, result)
    billing.must_hear(conv, line)
    return {"utterance": line}
