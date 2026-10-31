from _gen import *  # <AUTO GENERATED>
import re

import functions.api_client as api_client
import functions.idnv as idnv
from functions.handoff import transfer

FAIL_UTTERANCE = (
    "I'm sorry, I wasn't able to confirm your identity with those details. "
    "Let me put you through to a colleague who can help. One moment please."
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


MISMATCH_WORDING = (
    "Tell the caller only that the details don't match; never say you can't find, or are "
    "having trouble finding, an account. From now on pass only what the caller says after this "
    "reply, with an empty string for everything else: when they give their date of birth, pass "
    "account_number as an empty string until they say an account number again, even though they "
    "gave one before. "
)


def _next_step(result) -> str:
    """idnv's instruction for the next reply, passed through whole: its own wording says which
    details are kept and what to ask again, and its last sentence says to call verify_caller
    again. idnv.py speaks of a 'member ID', which in a bank is the caller's account number.
    After a mismatch, two lines go after the attempt label, before idnv's text: what not to say,
    and to pass only details given after the mismatch (RSN-1 otherwise re-sends the earlier
    account number with the new date of birth)."""
    say = result.say.replace("member ID", "account number")
    if result.outcome == "retry" and "don't match" in say:
        head, sep, rest = say.partition(": ")
        say = f"{head}{sep}{MISMATCH_WORDING}{rest}" if sep else MISMATCH_WORDING + say
    return say


@func_description(
    "Check who the caller is from the phone number on their account, their date of birth and their account number. Call it whenever the caller gives any of these, or confirms or corrects a number you read back, even if it's the same as before. Only this tool decides whether details match."
)
@func_parameter(
    "phone_number",
    "The phone number the caller gave THIS time, as they said it (words or digits), even if it sounds incomplete. Never add, guess or repeat digits. Empty if they gave no number.",
)
@func_parameter(
    "date_of_birth",
    "Their date of birth as YYYY-MM-DD if you can, otherwise as they said it. Empty if not given.",
)
@func_parameter(
    "account_number",
    "Their account number as they said it (words or digits). Empty if not given.",
)
@func_parameter(
    "caller_cannot_verify",
    "'true' only if the caller says they don't have or won't give these details. Otherwise 'false'.",
)
@func_parameter(
    "phone_confirmed",
    "'true' only if, in their latest reply, the caller clearly said yes to the phone number this tool told you to read back, or repeated that same number. An \"okay\", or anything unclear, is not a yes. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[
        ("One moment while I check those details.", 3),
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
    try:
        result = idnv.verify_strict(
            conv,
            phone_number,
            spoken_date(date_of_birth),
            idnv.spoken_digits_to_string(account_number) or account_number,
            lookup=_lookup(conv),
            caller_cannot_verify=str(caller_cannot_verify).strip().lower() == "true",
            phone_confirmed=str(phone_confirmed).strip().lower() == "true",
        )
    except Exception:
        conv.log.error("verify_caller lookup failed", exc_info=True)
        return transfer(
            conv,
            "API_ERROR",
            "I'm sorry, I'm having trouble looking up accounts right now. "
            "Let me put you through to a colleague. One moment please.",
        )

    if result.failed:
        return transfer(conv, result.handoff_reason, FAIL_UTTERANCE)

    if result.verified:
        target = idnv.take_resume(conv)
        first = (result.customer or {}).get("first_name", "")
        if target:
            conv.goto_flow(target)
            return (
                f"The caller is verified as {first}. Don't ask for anything they have already "
                "told you; carry on with their request in this same reply."
            )
        conv.exit_flow()
        return f"The caller is verified as {first}. Ask how you can help."

    if result.outcome == "read_back" and result.say.startswith("WAIT"):
        # A second call in the turn that read the number back: the caller hasn't answered yet.
        # Say the readback and end the turn here. On RSN-1 the model otherwise keeps calling
        # in the same turn, ignoring WAIT, until the turn runs out of steps and errors (422).
        # idnv doesn't count this call.
        return {"utterance": readback_question(conv)}

    return _next_step(result)


def readback_question(conv) -> str:
    return f"Is that phone number {idnv.spell_phone(idnv.state(conv)['phone'])}?"
