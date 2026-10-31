"""Bill pay rules, readbacks and the call-state block, shared by every task flow.

The flows stay one prompt and a few tools each because the rules live here:
- what a phone payment may be: more than zero, no more than the balance due,
  no more than MAX_PHONE_PAYMENT, from a payment method on file, today or up to
  MAX_DAYS_AHEAD days ahead;
- what the agent reads back: everything the first time, then only what changed
  (readback_text);
- the CALL STATE block every tool response ends with. On voice a step prompt is
  rendered once, when the step is entered, so state shown in the prompt would
  freeze; the latest tool response is always current.
"""

from _gen import *  # <AUTO GENERATED>
import re
from datetime import date, timedelta

import functions.api_client as api_client
import functions.idnv as idnv

# Payments by phone. Larger amounts go to the payments team.
MAX_PHONE_PAYMENT = 2500.00
# How far ahead a payment can be scheduled.
MAX_DAYS_AHEAD = 30

GATE_INSTRUCTION = (
    "Before you can help with this you need to confirm who the caller is: the phone number on "
    "their account, their date of birth and their account number. If they already gave any of "
    "these, call verify_caller with them now; otherwise ask for the phone number on their account."
)


@func_description("[UTIL] Bill pay rules and readback helpers, not callable directly")
def billing(conv: Conversation):
    return "Bill pay helpers module."


# --- Verification ------------------------------------------------------------


def gate(conv, resume: str) -> str | None:
    """Strict ID&V gate for an account task. None when the caller is verified."""
    if idnv.require(conv, resume, strength=idnv.STRICT) is None:
        return None
    return GATE_INSTRUCTION


def account(conv) -> dict | None:
    """The verified caller's account with its current balance, else None."""
    customer = idnv.customer(conv)
    if not customer or not idnv.is_verified(conv, idnv.STRICT):
        return None
    return api_client.get_account(conv, customer["id"])


def verified_account(conv) -> dict:
    """The verified caller's account. Only call after the strict gate has passed."""
    acct = account(conv)
    if acct is None:
        raise RuntimeError("verified_account called before strict ID&V")
    return acct


# --- Money --------------------------------------------------------------------


def parse_amount(value) -> float | None:
    """'$1,250.50', '1250.5', '50 dollars' -> float; None if there is no number."""
    text = str(value or "").replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    return round(float(match.group()), 2)


def say_money(amount: float) -> str:
    return f"${amount:,.2f}"


def amount_problem(amount: float | None, balance: float) -> str:
    """Why this payment amount can't be taken, as an instruction for the agent; '' if it can."""
    if amount is None or amount <= 0:
        return "Ask how much they'd like to pay."
    if amount > MAX_PHONE_PAYMENT:
        return (
            f"{say_money(amount)} is over the {say_money(MAX_PHONE_PAYMENT)} limit for a payment "
            "by phone. Tell the caller, and ask if they'd like to pay a smaller amount now or be "
            "put through to our payments team (if so, call handoff with handoff_reason="
            "'PAYMENT_OVER_PHONE_LIMIT'). If they give an amount, call update_payment with it."
        )
    if amount > balance:
        return (
            f"{say_money(amount)} is more than their balance of {say_money(balance)}, and we "
            "can't take more than is owed. Tell the caller, and ask how much they'd like to pay, "
            f"up to {say_money(balance)}. Then call update_payment with the amount they give."
        )
    return ""


def today(conv) -> date:
    try:
        return date.fromisoformat(conv.state.today_iso)
    except (TypeError, ValueError):
        return date.today()


def date_problem(conv, value: str) -> tuple[str, str]:
    """(YYYY-MM-DD, '') for an allowed payment date, or ('', instruction) if not."""
    text = str(value or "").strip().lower()
    first = today(conv)
    if text in ("", "today", "now", "asap"):
        return first.isoformat(), ""
    try:
        wanted = date.fromisoformat(text[:10])
    except ValueError:
        return "", "Ask which day they'd like the payment to go out: today, or a date."
    if wanted < first:
        return (
            "",
            "Payments can't be backdated. Ask if they'd like it to go today instead.",
        )
    if wanted > first + timedelta(days=MAX_DAYS_AHEAD):
        return "", (
            f"Payments can be scheduled up to {MAX_DAYS_AHEAD} days ahead. Ask for a date "
            "before then."
        )
    return wanted.isoformat(), ""


def match_method(said: str, methods: list[str]) -> str:
    """The payment method on file the caller means ('the Visa', 'ending 4242'), or ''."""
    words = set(re.findall(r"[a-z]+|\d+", str(said or "").lower())) - {
        "the",
        "my",
        "card",
        "ending",
        "account",
        "in",
    }
    if not words:
        return ""
    for method in methods:
        tokens = set(re.findall(r"[a-z]+|\d+", method.lower()))
        if words & tokens:
            return method
    return ""


_WORDS = "zero one two three four five six seven eight nine".split()


def say_digits(value: str) -> str:
    """'48211309' -> 'four eight two, one one three, zero nine'."""
    chars = [(_WORDS[int(c)] if c.isdigit() else c.upper()) for c in str(value or "")]
    groups = [" ".join(chars[i : i + 3]) for i in range(0, len(chars), 3)]
    return ", ".join(groups)


# --- Dates --------------------------------------------------------------------


def _ordinal(n: int) -> str:
    suffix = (
        "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


def say_date(iso: str) -> str:
    day = date.fromisoformat(iso)
    return f"{day.strftime('%A')}, {day.strftime('%B')} {_ordinal(day.day)}"


# --- Readbacks --------------------------------------------------------------


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


def changed_fields(conv, key: str, fields: list[tuple[str, str]]) -> list[str] | None:
    """The labels whose value changed since the last readback of `key`, or None if the caller
    hasn't heard one yet. Call it before readback_text, which stores the new values."""
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    last = store.get(key)
    if last is None:
        return None
    return [label for label, value in fields if value and last.get(label) != value]


def readback_is_current(conv, key: str, fields: list[tuple[str, str]]) -> bool:
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    current = {label: value for label, value in fields if value}
    return store.get(key) == current


def forget_readback(conv, key: str) -> None:
    store = dict(conv.state.readbacks) if isinstance(conv.state.readbacks, dict) else {}
    store.pop(key, None)
    conv.state.readbacks = store
    asked = (
        dict(conv.state.asked_turns) if isinstance(conv.state.asked_turns, dict) else {}
    )
    asked.pop(key, None)
    conv.state.asked_turns = asked


# --- Same-turn marker --------------------------------------------------------
# A write's yes-or-no question and the caller's answer are in different turns. At tool time
# conv.history holds only earlier turns, so its length grows once the caller has replied. The
# length is used only as that marker, never the content, as idnv does for the phone readback.

NOT_DONE_YET = "NOT DONE YET: wait for the caller's answer to the yes-or-no question, then call again."


def history_turn(conv) -> int | None:
    try:
        return len(conv.history)
    except Exception:
        return None


def mark_asked(conv, key: str) -> None:
    """Remember the turn in which the yes-or-no question for `key` was asked."""
    asked = (
        dict(conv.state.asked_turns) if isinstance(conv.state.asked_turns, dict) else {}
    )
    asked[key] = history_turn(conv)
    conv.state.asked_turns = asked


def same_turn_as_question(conv, key: str) -> bool:
    """True while the caller can't yet have answered the yes-or-no question for `key`."""
    asked = conv.state.asked_turns if isinstance(conv.state.asked_turns, dict) else {}
    turn = history_turn(conv)
    return turn is not None and asked.get(key) is not None and turn == asked.get(key)


# --- Text confirmations ------------------------------------------------------
# The offer to text the calling number is a yes-or-no question like a readback: its turn is
# stored (sms["asked_turn"]), so a yes in the same turn sends nothing.

TEXT_CALLING_NUMBER_QUESTION = (
    "Shall I text it to the number you're calling from, yes or no?"
)
TEXT_CALLING_NUMBER_OFFER = (
    f'Ask the caller, in these words: "{TEXT_CALLING_NUMBER_QUESTION}" Then wait for their '
    "answer. On a clear yes, call send_text with use_calling_number 'true'; if they give another "
    "number, call send_text with it as they said it, even if it sounds incomplete. Read back "
    "only what send_text returns."
)

# --- Call state -------------------------------------------------------------


def call_state(conv, task_lines: list[str], next_line: str) -> str:
    lines = [
        "CALL STATE (this replaces any earlier copy; never read it aloud)",
        f"- {idnv.state_line(conv).replace('member ID', 'account number')}",
    ]
    lines += [f"- {line}" for line in task_lines if line]
    lines.append(f"NEXT: {next_line}")
    return "\n".join(lines)


def record_transaction(conv, summary: str, confirmation: str) -> None:
    """Keep the last payment for the confirmation text message."""
    conv.state.last_transaction_summary = summary
    conv.state.last_confirmation_number = confirmation
