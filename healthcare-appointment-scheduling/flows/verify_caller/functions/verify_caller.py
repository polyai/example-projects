from _gen import *  # <AUTO GENERATED>
import re

import functions.api_client as api_client
import functions.appointments as appointments
import functions.idnv as idnv
from functions.handoff import handoff

FAIL_UTTERANCE = (
    "I'm sorry, I wasn't able to confirm your details. I'll put you through to our scheduling "
    "team, who can help. One moment, please."
)
DECLINED_UTTERANCE = (
    "No problem. Our scheduling team can help confirm your details another way. I'll put you "
    "through now. One moment, please."
)
LOOKUP_ERROR_UTTERANCE = (
    "I'm sorry, I'm having trouble looking up patient records right now. I'll put you through "
    "to our scheduling team, who can help. One moment, please."
)

_DIGIT_WORDS = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9",
}  # fmt: skip
_REPEAT = {"double": 2, "triple": 3}


def spoken_id(value) -> str:
    """'H C four eight two one three' -> 'HC48213'. Digit words become digits,
    single letters are kept, and anything already alphanumeric passes through."""
    out, repeat = [], 1
    for token in re.findall(r"[A-Za-z]+|\d+", str(value or "")):
        word = token.lower()
        if word in _REPEAT:
            repeat = _REPEAT[word]
            continue
        piece = _DIGIT_WORDS.get(word, token)
        out.append(piece * repeat if len(piece) == 1 else piece)
        repeat = 1
    return "".join(out).upper()


_MONTHS = "january february march april may june july august september october november december".split()
_UNITS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
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
    """['twenty', 'second'] -> 22; ['eighty', 'five'] -> 85; ['oh', 'five'] -> 5."""
    total, seen = 0, False
    for w in words:
        if w in ("oh", "o"):
            seen = True
        elif w in _TENS:
            total += _TENS[w]
            seen = True
        elif w in _ORDINALS:
            total += _ORDINALS[w]
            seen = True
        elif w in _UNITS:
            total += _UNITS.index(w)
            seen = True
        elif w.isdigit():
            total += int(w)
            seen = True
        elif w != "and":
            return None
    return total if seen else None


def _spoken_year(words: list[str]) -> int | None:
    """'nineteen eighty five' -> 1985, 'two thousand and three' -> 2003, '1985' -> 1985."""
    if len(words) == 1 and words[0].isdigit():
        return int(words[0])
    if words[:2] == ["two", "thousand"]:
        rest = _small_number(words[2:]) if words[2:] else 0
        return None if rest is None else 2000 + rest
    if words and words[0] in ("nineteen", "twenty"):
        rest = _small_number(words[1:])
        return (
            None if rest is None else (1900 if words[0] == "nineteen" else 2000) + rest
        )
    return None


def spoken_date(value) -> str:
    """'March fifteenth, nineteen eighty-five' -> '1985-03-15'. Anything else is
    passed on unchanged for functions/idnv.py to parse (or ask again)."""
    text = str(value or "").strip()
    words = re.findall(r"[a-z]+|\d+", text.lower().replace("-", " "))
    month = next((i for i, w in enumerate(words) if w in _MONTHS), None)
    if month is None:
        return text
    after = [
        w for w in words[month + 1 :] if w not in ("the", "of", "st", "nd", "rd", "th")
    ]
    before = [
        w for w in words[:month] if w not in ("the", "of", "st", "nd", "rd", "th")
    ]
    # "March fifteenth nineteen eighty five" or "the fifteenth of March nineteen eighty five"
    day_words, year_words = (before, after) if before else (after[:1], after[1:])
    if (
        not before
        and after
        and after[0] in _TENS
        and len(after) > 1
        and after[1] in _ORDINALS
    ):
        day_words, year_words = after[:2], after[2:]
    if not before and after and after[0].isdigit() and len(after) > 1:
        day_words, year_words = after[:1], after[1:]
    day, year = _small_number(day_words), _spoken_year(year_words)
    if not day or not year or not 1 <= day <= 31:
        return text
    return f"{year:04d}-{_MONTHS.index(words[month]) + 1:02d}-{day:02d}"


def _lookup(conv):
    return lambda phone: api_client.find_patients_by_phone(conv, phone)


@func_description(
    "Check who the caller is from the phone number on their patient record, their date of birth and their member ID. Call it whenever the caller gives or corrects any of these, or answers the question it asked."
)
@func_parameter(
    "phone_number",
    "The phone number the caller gave this time, as they said it (words or digits). Never add, guess or repeat digits.",
)
@func_parameter(
    "date_of_birth",
    "Their date of birth as YYYY-MM-DD if you can, otherwise as they said it.",
)
@func_parameter(
    "member_id", "Their member ID, letters and digits only, e.g. 'HC48213'."
)
@func_parameter(
    "caller_cannot_verify",
    "'true' only if the caller says they don't have or won't give these details, or that there is no other number to try.",
)
@func_parameter(
    "phone_confirmed",
    "'true' if the caller's latest reply agreed to the question this tool asked about their number: whether the number they're calling from is the one on their record, or (after a miss) that it's the same one. A yes or an acknowledgement ('okay', 'sure', 'yeah') to that question is agreement; pass no phone number with it.",
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
    member_id: str,
    caller_cannot_verify: str,
    phone_confirmed: str,
):
    # After a miss the model tends to pass the failed details again. The design asks for them
    # again one at a time (number, date of birth, member ID), so until each has been asked
    # again, a call keeps only the next one.
    redo = list(conv.state.idnv_redo or [])
    if redo:
        given = {
            "phone": bool(str(phone_number or "").strip()) or phone_confirmed == "true",
            "date_of_birth": bool(str(date_of_birth or "").strip()),
            "member_id": bool(str(member_id or "").strip()),
        }
        if redo[0] != "date_of_birth":
            date_of_birth = ""
        if redo[0] != "member_id":
            member_id = ""
        if redo[0] != "phone":
            phone_number, phone_confirmed = "", "false"
        if given[redo[0]]:
            redo.pop(0)
        conv.state.idnv_redo = redo
    try:
        result = idnv.verify_strict(
            conv,
            phone_number,
            spoken_date(date_of_birth),
            spoken_id(member_id),
            lookup=_lookup(conv),
            caller_cannot_verify=str(caller_cannot_verify).strip().lower() == "true",
            phone_confirmed=str(phone_confirmed).strip().lower() == "true",
            caller_id_question=appointments.CALLER_ID_QUESTION,
        )
    except Exception:
        conv.log.error("verify_caller lookup failed", exc_info=True)
        return handoff(conv, "IDNV_API_ERROR", LOOKUP_ERROR_UTTERANCE)

    if result.failed:
        declined = result.handoff_reason == idnv.FAILED_REASON_DECLINED
        return handoff(
            conv,
            result.handoff_reason,
            DECLINED_UTTERANCE if declined else FAIL_UTTERANCE,
        )

    if result.verified:
        target = idnv.take_resume(conv)
        first = (result.customer or {}).get("first_name", "")
        if target:
            conv.goto_flow(target)
            return (
                f'VERIFIED as {first}. Say "Thanks, {first}." and carry on with their request in '
                "this same reply, without asking again for anything they've already told you."
            )
        conv.exit_flow()
        return f'VERIFIED as {first}. Say "Thanks, {first}." and ask how you can help.'

    if result.outcome == "wait":
        # WAIT: called again in the turn the question was asked. Say the question and end the turn,
        # so the model can't keep calling (on RSN-1 a same-turn loop ends in a 422).
        return {"utterance": appointments.idnv_wording(result.utterance)}

    if result.outcome == "retry" and result.missing == [
        "phone",
        "date_of_birth",
        "member_id",
    ]:
        conv.state.idnv_redo = ["phone", "date_of_birth", "member_id"]
    return appointments.idnv_wording(f"{idnv.state_line(conv)}.\n{result.say}")
