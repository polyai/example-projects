"""Bill pay rules, spoken formats, the ID&V gate and the call-state block.

The flows stay one prompt and a few tools each because the rules live here:
- what a phone payment may be: more than zero, no more than the balance due,
  no more than MAX_PHONE_PAYMENT, from a payment method on file, today or up to
  MAX_DAYS_AHEAD days ahead (functions/payments.py applies them);
- how money, cards, dates and numbers are said ("$275.50", "Visa ending four
  two four two", "Friday the 6th", "four eight two one, one three zero nine");
- the balance sentence and its closing question;
- the same-turn marker that keeps a yes from counting before the caller heard
  the question;
- the CALL STATE block tool responses end with. On voice a step prompt is
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

# ID&V wording (design 2.1). The caller-ID question is passed to idnv, which only asks it when
# the caller ID is usable; the model can't see that, so the gate's return names the question.
CALLER_ID_QUESTION = "Is your account under the number you're calling from?"
PHONE_QUESTION = "What's the phone number on your account?"
GATE_OPENER = (
    "Sure, I can help with that. I'll just need to confirm a few details first."
)


@func_description("[UTIL] Bill pay rules and spoken formats, not callable directly")
def billing(conv: Conversation):
    return "Bill pay helpers module."


# --- Verification ------------------------------------------------------------


def gate(conv, resume: str) -> str | None:
    """Strict ID&V gate for an account task. None when the caller is verified; otherwise the
    caller is sent to verify_caller and this returns the opening line and the first question."""
    if (
        idnv.require(
            conv, resume, strength=idnv.STRICT, caller_id_question=CALLER_ID_QUESTION
        )
        is None
    ):
        return None
    question = (
        CALLER_ID_QUESTION
        if idnv.state(conv)["pending"] == "caller_id"
        else PHONE_QUESTION
    )
    return (
        "Before you can help with this you need to confirm who the caller is: the phone number "
        "on their account, their date of birth and their account number. If they already gave "
        "any of these, call verify_caller with them now, before you reply. Otherwise say, in "
        f'words like these: "{GATE_OPENER} {question}" Never say the number they\'re calling '
        f"from. Then call verify_caller with whatever they say, {'a yes included' if question == CALLER_ID_QUESTION else 'as they said it'}."
    )


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


def first_name(conv) -> str:
    return (idnv.customer(conv) or {}).get("first_name", "")


# --- Money --------------------------------------------------------------------

ALL = "all"  # parse_amount's answer for "all of it", "the full amount", "pay it off"

_ALL_WORDS = re.compile(
    r"\b(all|full|whole|entire|everything|total|pay (it|that|this) off|the balance)\b",
    re.I,
)
_UNITS = {
    w: i
    for i, w in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
        "fifteen sixteen seventeen eighteen nineteen".split()
    )
}
_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def _words_to_number(text: str) -> float | None:
    """'a hundred', 'seventy-five', 'two thousand five hundred' -> number; None if no number words."""
    words = re.findall(r"[a-z]+", text.lower().replace("-", " "))
    total, current, seen = 0, 0, False
    for w in words:
        if w in _UNITS:
            current += _UNITS[w]
            seen = True
        elif w in _TENS:
            current += _TENS[w]
            seen = True
        elif w == "hundred":
            current = (current or 1) * 100
            seen = True
        elif w == "thousand":
            total += (current or 1) * 1000
            current = 0
            seen = True
        elif w == "a" or w == "and":
            continue
        elif seen:
            break
    return float(total + current) if seen else None


def parse_amount(value) -> float | str | None:
    """'$1,250.50', '1250.5', '50 dollars', 'a hundred' -> float; 'all of it', 'the full amount',
    'pay it off' -> ALL; None if there is no amount."""
    text = str(value or "").replace(",", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", text)
    if match:
        return round(float(match.group()), 2)
    if _ALL_WORDS.search(text):
        return ALL
    number = _words_to_number(text)
    return round(number, 2) if number else None


def say_money(amount: float) -> str:
    """Natural amounts: '$150', '$275.50', '$2,500'. Cents only when there are some."""
    value = round(float(amount or 0), 2)
    if value == int(value):
        return f"${int(value):,}"
    return f"${value:,.2f}"


# --- Digits, cards and phone numbers -------------------------------------------

_WORDS = "zero one two three four five six seven eight nine".split()


def _spell(chars: str) -> str:
    return " ".join(_WORDS[int(c)] if c.isdigit() else c.upper() for c in chars)


def say_digits(value: str) -> str:
    """Confirmation numbers in fours: '48211309' -> 'four eight two one, one three zero nine'."""
    chars = re.sub(r"[^A-Za-z0-9]", "", str(value or ""))
    return ", ".join(_spell(chars[i : i + 4]) for i in range(0, len(chars), 4))


_TOLL_FREE = {"800", "888", "877", "866", "855", "844", "833"}


def say_phone(value: str) -> str:
    """A phone number we say first, digit by digit in 3-3-4 groups; a toll-free prefix as
    'one eight hundred'. '1-800-555-0123' -> 'one eight hundred, five five five, zero one two
    three'."""
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return _spell(digits)
    area, rest = digits[:3], f"{_spell(digits[3:6])}, {_spell(digits[6:])}"
    if area == "800":
        return f"one eight hundred, {rest}"
    if area in _TOLL_FREE:
        return f"one {_spell(area)}, {rest}"
    return f"{_spell(area)}, {rest}"


_METHOD = re.compile(r"^(?P<kind>.*?)\s+ending\s+(?P<last>\d{4})$", re.I)


def say_method(method: str) -> str:
    """'Visa ending 4242' -> 'Visa ending four two four two'."""
    m = _METHOD.match(str(method or "").strip())
    return f"{m['kind']} ending {_spell(m['last'])}" if m else str(method or "")


def short_method(method: str) -> str:
    """'Visa ending 4242' -> 'Visa'; 'checking account ending 6789' -> 'checking account'."""
    m = _METHOD.match(str(method or "").strip())
    return m["kind"] if m else str(method or "")


_METHOD_NOISE = {
    "the",
    "my",
    "card",
    "ending",
    "account",
    "in",
    "one",
    "on",
    "with",
    "use",
    "pay",
    "a",
}
_NEW_METHOD = re.compile(r"\b(new|different|another|other|someone else'?s?)\b", re.I)


def match_method(said: str, methods: list[str]) -> str | None:
    """The method on file the caller means ('the Visa', 'checking', 'ending 4242').
    '' when they named one that isn't on file (a new or different card, digits that aren't on
    file); None when what they said doesn't pick one ('the card', with nothing else)."""
    text = str(said or "")
    if not text.strip():
        return None
    if _NEW_METHOD.search(text):
        return ""
    digits = idnv.spoken_digits_to_string(text)
    if len(digits) >= 4:
        for method in methods:
            m = _METHOD.match(method)
            if m and digits.endswith(m["last"]):
                return method
        return ""
    words = set(re.findall(r"[a-z]+", text.lower())) - _METHOD_NOISE
    if "bank" in words:
        words |= {"checking", "savings"}
    if not words:
        return None
    hits = [m for m in methods if words & set(re.findall(r"[a-z]+", m.lower()))]
    if len(hits) == 1:
        return hits[0]
    return None if hits else ""


# --- Dates --------------------------------------------------------------------


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


def say_day(conv, iso: str) -> str:
    """'today', 'tomorrow', 'Friday the 6th' within two weeks either way, then
    'Wednesday, December 2nd'. Never the year."""
    day = date.fromisoformat(iso)
    delta = (day - today(conv)).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    if delta == -1:
        return "yesterday"
    if abs(delta) <= 14:
        return f"{day.strftime('%A')} the {_ordinal(day.day)}"
    return f"{day.strftime('%A')}, {day.strftime('%B')} {_ordinal(day.day)}"


def say_on(conv, iso: str) -> str:
    """'today', 'tomorrow', or 'on Friday the 6th'."""
    said = say_day(conv, iso)
    return said if said in ("today", "tomorrow", "yesterday") else f"on {said}"


def say_the(iso: str) -> str:
    """'the 16th', for a note that only needs the day of the month."""
    return f"the {_ordinal(date.fromisoformat(iso).day)}"


_MONTHS = "january february march april may june july august september october november december".split()
_WEEKDAYS = "monday tuesday wednesday thursday friday saturday sunday".split()
_ORDINAL_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
    "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13,
    "fourteenth": 14, "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
    "nineteenth": 19, "twentieth": 20, "thirtieth": 30,
}  # fmt: skip


def _day_of_month(text: str) -> int | None:
    m = re.search(r"\b(\d{1,2})(st|nd|rd|th)?\b", text)
    if m:
        return int(m.group(1))
    words = re.findall(r"[a-z]+", text.replace("-", " "))
    total = 0
    for i, w in enumerate(words):
        if w in _ORDINAL_WORDS:
            total += _ORDINAL_WORDS[w]
            if i and words[i - 1] in ("twenty", "thirty"):
                total += 20 if words[i - 1] == "twenty" else 30
            return total
    return None


def resolve_day(conv, day_said: str) -> tuple[str, str]:
    """The caller's words for a day -> (YYYY-MM-DD or '', weekday named or '').

    A date in words ("the 20th of December", "December 1st", "the 1st") wins; a weekday alone
    ("this Friday") is the next one after today; "today" and "tomorrow" are what they say."""
    text = str(day_said or "").lower()
    first = today(conv)
    weekday = next((w for w in _WEEKDAYS if w in text), "")
    if not text.strip():
        return "", ""
    if re.search(r"\b(today|now|right away|asap)\b", text):
        return first.isoformat(), weekday
    if "tomorrow" in text:
        return (first + timedelta(days=1)).isoformat(), weekday
    month = next(
        (i + 1 for i, m in enumerate(_MONTHS) if re.search(rf"\b{m[:3]}", text)), 0
    )
    dom = _day_of_month(re.sub(r"\b(" + "|".join(_WEEKDAYS) + r")\b", " ", text))
    if dom and 1 <= dom <= 31:
        if month:
            year = first.year + (1 if (first.month - month) > 6 else 0)
        else:
            month = first.month if dom >= first.day else first.month % 12 + 1
            year = first.year + (1 if month < first.month else 0)
        try:
            return date(year, month, dom).isoformat(), weekday
        except ValueError:
            return "", weekday
    if weekday:
        ahead = (_WEEKDAYS.index(weekday) - first.weekday()) % 7 or 7
        return (first + timedelta(days=ahead)).isoformat(), weekday
    return "", ""


def date_problem(conv, pay_date: str, day_said: str = "") -> tuple[str, str]:
    """(YYYY-MM-DD, '') for an allowed payment date, or ('', instruction) if not. The caller's
    own words for the day (day_said) beat the model's date; a weekday that doesn't match the
    date is asked about, never guessed."""
    first = today(conv)
    said_iso, weekday = resolve_day(conv, day_said)
    text = str(pay_date or "").strip().lower()
    wanted_iso = said_iso
    if not wanted_iso:
        if text in ("", "today", "now", "asap"):
            wanted_iso = first.isoformat()
        else:
            try:
                wanted_iso = date.fromisoformat(text[:10]).isoformat()
            except ValueError:
                return "", 'Ask: "What day would you like it to go out?"'
    wanted = date.fromisoformat(wanted_iso)
    if weekday and wanted.strftime("%A").lower() != weekday:
        return "", (
            f"The caller said {weekday.capitalize()}, but that date is a "
            f'{wanted.strftime("%A")}. Ask which they meant: "Just to check, did you mean '
            f'{say_day(conv, wanted_iso)}?" Then call update_payment again with their answer.'
        )
    if wanted < first:
        return "", (
            'Say: "I can\'t backdate a payment, but I can make it today. Would that work?" '
            "A yes → call update_payment with pay_date 'today'."
        )
    latest = first + timedelta(days=MAX_DAYS_AHEAD)
    if wanted > latest:
        return "", (
            f'Say: "I can schedule a payment up to {MAX_DAYS_AHEAD} days ahead, so the latest '
            f'would be {say_day(conv, latest.isoformat())}. Would that work?" A yes → call '
            f"update_payment with pay_date {latest.isoformat()}; another day → that day."
        )
    return wanted.isoformat(), ""


# --- Balance ------------------------------------------------------------------


def balance_due_unscheduled(acct: dict) -> bool:
    return acct.get("balance", 0) > 0 and not (acct.get("scheduled_payments") or [])


def balance_sentence(conv, acct: dict, short: bool = False) -> str:
    """The balance and due date in one sentence, and a second only for scheduled payments.
    short: the payment flow's form ('Your balance is $150, due on Monday the 16th.')."""
    balance = round(float(acct.get("balance", 0)), 2)
    if balance < 0:
        return f"You're in credit by {say_money(-balance)}."
    if balance == 0:
        return "You don't owe anything at the moment."
    due = acct.get("due_date") or ""
    if due and date.fromisoformat(due) < today(conv):
        text = f"Your balance of {say_money(balance)} was due {say_on(conv, due)}."
    elif short:
        text = f"Your balance is {say_money(balance)}, due {say_on(conv, due)}."
    else:
        text = (
            f"Your balance is {say_money(balance)}, and it's due {say_on(conv, due)}."
        )
    scheduled = acct.get("scheduled_payments") or []
    if scheduled and not short:
        if len(scheduled) == 1:
            p = scheduled[0]
            when = "that day" if p["date"] == due else say_on(conv, p["date"])
            text += f" You've also got a {say_money(p['amount'])} payment set to go out {when}."
        else:
            items = ", and ".join(
                f"{say_money(p['amount'])} {say_on(conv, p['date'])}" for p in scheduled
            )
            text += f" You've also got payments set to go out: {items}."
    return text


def balance_instruction(conv, acct: dict, opener: str = "") -> str:
    """What the agent says for the balance: the sentence, then the closing question."""
    closing = (
        "Would you like to make a payment?"
        if balance_due_unscheduled(acct)
        else "Is there anything else I can help with?"
    )
    conv.state.balance_heard = True
    said = f"{opener} {balance_sentence(conv, acct)} {closing}".strip()
    return (
        f'Say: "{said}" Add nothing the tool didn\'t give you. If they want to pay, or say yes '
        'or "okay" to "Would you like to make a payment?", call start_make_payment.'
    )


# --- Same-turn marker --------------------------------------------------------
# A write's question and the caller's answer are in different turns. At tool time conv.history
# holds only earlier turns, so its length grows once the caller has replied. The length is used
# only as that marker, never the content, as idnv does.

NOT_DONE_YET = (
    "NOT DONE YET: the caller hasn't heard the question yet. Say it, wait for their answer, "
    "then call again."
)


def history_turn(conv) -> int | None:
    try:
        return len(conv.history)
    except Exception:
        return None


def mark_asked(conv, key: str) -> None:
    """Remember the turn in which the question for `key` was asked."""
    asked = (
        dict(conv.state.asked_turns) if isinstance(conv.state.asked_turns, dict) else {}
    )
    asked[key] = history_turn(conv)
    conv.state.asked_turns = asked


def same_turn_as_question(conv, key: str) -> bool:
    """True while the caller can't yet have answered the question for `key`."""
    asked = conv.state.asked_turns if isinstance(conv.state.asked_turns, dict) else {}
    turn = history_turn(conv)
    return turn is not None and asked.get(key) is not None and turn == asked.get(key)


def forget_asked(conv, key: str) -> None:
    asked = (
        dict(conv.state.asked_turns) if isinstance(conv.state.asked_turns, dict) else {}
    )
    asked.pop(key, None)
    conv.state.asked_turns = asked


# --- Lines that must be heard ---------------------------------------------------


def must_hear(conv, line: str) -> None:
    """Keep a line that must be heard (a done line with a confirmation number). If the model
    ends the call in the same turn, goodbye_and_hangup says it again before the goodbye."""
    conv.state.must_hear = {"line": line, "turn": history_turn(conv)}


def unheard_line(conv) -> str:
    kept = conv.state.must_hear if isinstance(conv.state.must_hear, dict) else {}
    if (
        kept.get("line")
        and kept.get("turn") is not None
        and kept["turn"] == history_turn(conv)
    ):
        return kept["line"]
    return ""


# --- Call state -------------------------------------------------------------


def call_state(conv, task_lines: list[str], next_line: str) -> str:
    lines = [
        "CALL STATE (this replaces any earlier copy; never read it aloud)",
        f"- {idnv.state_line(conv).replace('member ID', 'account number').replace('member id', 'account number')}",
    ]
    lines += [f"- {line}" for line in task_lines if line]
    lines.append(f"NEXT: {next_line}")
    return "\n".join(lines)


def record_transaction(conv, summary: str, confirmation: str) -> None:
    """Keep the last payment for the confirmation text message and the goodbye."""
    conv.state.last_transaction_summary = summary
    conv.state.last_confirmation_number = confirmation
    conv.state.paid_this_call = True
