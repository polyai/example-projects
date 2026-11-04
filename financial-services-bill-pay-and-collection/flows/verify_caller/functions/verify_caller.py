from _gen import *  # <AUTO GENERATED>
import re

import functions.api_client as api_client
import functions.billing as billing
import functions.idnv as idnv
import functions.payments as payments
from functions.handoff import transfer

# Lines held in code (design 2.1 and section 3).
FAIL_UTTERANCE = (
    "I'm sorry, I wasn't able to confirm your details, so I'll put you through to a colleague "
    "who can help. One moment, please."
)
DECLINED_UTTERANCE = (
    "That's okay. A colleague can help you another way. I'll put you through now. One moment, "
    "please."
)
API_ERROR_UTTERANCE = (
    "I'm sorry, I can't look up accounts right now, so I'll put you through to a colleague who "
    "can help. One moment, please."
)
NOT_FULL_NUMBER = (
    "Sorry, I didn't catch all of that. Could you give me the full number, starting with the "
    "area code?"
)
NO_ACCOUNT_NUMBER = (
    "If they don't have it to hand, say: \"No problem. It's on your statements, and in the app "
    'under My details. Would you like a moment to find it?" If they want a moment, call '
    "user_needs_time. Only if they don't want to look, call verify_caller with "
    "caller_cannot_verify='true'."
)

_MONTHS = "january february march april may june july august september october november december".split()
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
_ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
    "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13,
    "fourteenth": 14, "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
    "nineteenth": 19, "twentieth": 20, "thirtieth": 30,
}  # fmt: skip


def _small_number(words: list[str]) -> int | None:
    """'twenty one' / 'twenty first' / 'eighty five' -> int (0-99)."""
    total, seen = 0, False
    for w in words:
        if w in _TENS:
            total += _TENS[w]
        elif w in _UNITS:
            total += _UNITS[w]
        elif w in _ORDINALS:
            total += _ORDINALS[w]
        else:
            return None
        seen = True
    return total if seen else None


def spoken_date(value) -> str:
    """'March fifteenth, nineteen eighty-five' -> '1985-03-15'. Anything else is returned
    unchanged for idnv.normalize_dob to parse (digits, ISO, '15 March 1985')."""
    text = str(value or "").lower().replace("-", " ").replace(",", " ")
    words = [
        w for w in re.findall(r"[a-z]+|\d+", text) if w not in ("the", "of", "and")
    ]
    month = next((i + 1 for i, m in enumerate(_MONTHS) if m in words), 0)
    if not month or any(w.isdigit() for w in words):
        return str(value or "")
    rest = [w for w in words if w != _MONTHS[month - 1]]
    for split in range(1, min(3, len(rest)) + 1):
        day, year_words = _small_number(rest[:split]), rest[split:]
        if not day or not 1 <= day <= 31 or not year_words:
            continue
        if year_words[:2] == ["two", "thousand"]:
            tail = _small_number(year_words[2:]) if year_words[2:] else 0
            year = 2000 + tail if tail is not None else None
        else:
            century, decade = (
                _small_number(year_words[:1]),
                _small_number(year_words[1:]),
            )
            year = century * 100 + decade if century and decade is not None else None
        if year and 1900 <= year <= 2100:
            return f"{year:04d}-{month:02d}-{day:02d}"
    return str(value or "")


def _lookup(conv):
    return lambda phone: api_client.find_accounts_by_phone(conv, phone)


def _ask(question: str, extra: str = "") -> str:
    return f'Ask: "{question}" {extra}{idnv.CALL_AGAIN}'.replace("  ", " ")


def _next_step(conv, result) -> str:
    """The next question, in the design's words. idnv.py decides what is missing and counts
    every miss; it speaks of a 'member ID', which in a bank is the caller's account number."""
    say = result.say.replace("member ID", "account number")
    if result.outcome == "retry" and "NOT A FULL NUMBER" in say:
        head, _, _ = say.partition(": ")
        return (
            f'{head}: that wasn\'t a full phone number. Say: "{NOT_FULL_NUMBER}" Never repeat the '
            f"digits they said. {idnv.CALL_AGAIN}"
        )
    if result.outcome != "need" or not result.missing or not say.startswith("Ask for"):
        return say
    again = idnv.state(conv)["mismatches"] > 0
    first = result.missing[0]
    if first == "phone":
        return _ask(billing.PHONE_QUESTION, "Never read it back. ")
    if first == "date_of_birth":
        return _ask(
            "Thanks. And your date of birth again?"
            if again
            else "Thanks. And what's your date of birth?",
            'If they ask why, say "It\'s just so I can keep your account safe." and ask again. ',
        )
    return _ask(
        "And your account number again?"
        if again
        else "And what's your account number?",
        f"{NO_ACCOUNT_NUMBER} ",
    )


def _fresh_only(conv, date_of_birth: str, account_number: str) -> tuple[str, str]:
    """After a mismatch, a detail equal to the one that just failed is dropped unless the tool
    has asked for it again: RSN-1 re-sends the earlier date of birth or account number with the
    new phone answer. Once asked again, whatever the caller says counts, the same value included."""
    failed = conv.state.idnv_failed if isinstance(conv.state.idnv_failed, dict) else {}
    asked = conv.state.idnv_asked or ""
    dob = idnv.normalize_dob(spoken_date(date_of_birth))
    acct = idnv.normalize_id(
        idnv.spoken_digits_to_string(account_number) or account_number
    )
    if dob and dob == failed.get("dob") and asked != "date_of_birth":
        date_of_birth = ""
    if acct and acct == failed.get("member_id") and asked != "member_id":
        account_number = ""
    return date_of_birth, account_number


def _remember(conv, result, before: dict) -> None:
    """What the tool asks next, and the details a mismatch just failed on."""
    if result.outcome == "retry" and "don't match" in result.say:
        conv.state.idnv_failed = before
    conv.state.idnv_asked = (
        (result.missing or [""])[0] if result.outcome in ("need", "retry") else ""
    )


def _verified_line(conv, first: str, target: str) -> str:
    """What the caller hears on success: the thanks, then the task, in the same reply."""
    opener = (
        f"Thanks, {first}, that's all confirmed."
        if first
        else "Thanks, that's all confirmed."
    )
    if target == "account_balance":
        acct = billing.verified_account(conv)
        conv.write_metric("BALANCE_GIVEN")
        return billing.balance_instruction(conv, acct, opener)
    if target == "make_payment":
        return payments.entry_instruction(conv, opener)
    if target:
        return f'Say "{opener}" Then carry on with their request in this same reply.'
    return f'Say: "{opener} How can I help?"'


@func_description(
    "Check who the caller is from the phone number on their account, their date of birth and their account number. Call it whenever the caller answers one of its questions, with whatever they said, even if it's the same as before. Only this tool decides whether details match."
)
@func_parameter(
    "phone_number",
    "The phone number the caller gave THIS time, as they said it (words or digits), even if it sounds incomplete. Never add, guess or repeat digits.",
)
@func_parameter(
    "date_of_birth",
    "Their date of birth as YYYY-MM-DD if you can, otherwise as they said it.",
)
@func_parameter(
    "account_number", "Their account number as they said it (words or digits)."
)
@func_parameter(
    "caller_cannot_verify",
    "'true' only if the caller won't give a detail after hearing why it's needed, or doesn't have their account number and doesn't want to look for it. Otherwise 'false'.",
)
@func_parameter(
    "phone_confirmed",
    "'true' if the caller's latest reply was a yes, or an acknowledgement ('okay', 'sure', 'yeah'), to this tool's question about the number they're calling from, or said it's the same number after the details didn't match. Then pass no phone number. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[
        ("Just a moment while I check those details.", 3),
        ("Nearly there.", 3),
    ],
)
def verify_caller(
    conv: Conversation,
    flow: Flow,
    phone_number: str,
    date_of_birth: str,
    account_number: str,
    caller_cannot_verify: str,
    phone_confirmed: str,
):
    date_of_birth, account_number = _fresh_only(conv, date_of_birth, account_number)
    s = idnv.state(conv)
    before = {
        "dob": idnv.normalize_dob(spoken_date(date_of_birth)) or s["dob"],
        "member_id": idnv.normalize_id(
            idnv.spoken_digits_to_string(account_number) or account_number
        )
        or s["member_id"],
    }
    try:
        result = idnv.verify_strict(
            conv,
            phone_number,
            spoken_date(date_of_birth),
            idnv.spoken_digits_to_string(account_number) or account_number,
            lookup=_lookup(conv),
            caller_cannot_verify=str(caller_cannot_verify).strip().lower() == "true",
            phone_confirmed=str(phone_confirmed).strip().lower() == "true",
            caller_id_question=billing.CALLER_ID_QUESTION,
        )
    except Exception:
        conv.log.error("verify_caller lookup failed", exc_info=True)
        return transfer(conv, "API_ERROR", API_ERROR_UTTERANCE)

    if result.failed:
        line = (
            DECLINED_UTTERANCE
            if result.handoff_reason == idnv.FAILED_REASON_DECLINED
            else FAIL_UTTERANCE
        )
        return transfer(conv, result.handoff_reason, line)

    if result.outcome == "wait":
        # WAIT: called again in the turn it asked a question; the caller hasn't answered. Speak the
        # question and end the turn; RSN-1 otherwise keeps calling until the turn errors (422).
        return {"utterance": result.utterance}

    if result.verified:
        target = idnv.take_resume(conv)
        first = (result.customer or {}).get("first_name", "")
        line = _verified_line(conv, first, target)
        conv.state.entry_said_turn = billing.history_turn(conv)
        if target:
            conv.goto_flow(target)
        else:
            conv.exit_flow()
        return line

    _remember(conv, result, before)
    return _next_step(conv, result)
