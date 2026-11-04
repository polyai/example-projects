"""Caller identity verification (ID&V): the shared pattern for the onboarding templates.

Two strengths:
- LAX: the caller ID (ANI) matches an account, or the caller gives the phone
  number on the account plus the account holder's name. For low-risk tasks:
  bookings, order status, field service visits.
- STRICT: phone number + date of birth + member/account ID, all three matching
  one account. For personal data and money: healthcare, banking, cards.

Everything that decides the outcome lives here, in code: input normalisation,
matching, retry limits and the fail path. The model only passes on what the
caller said and says what the result tells it to. A template wires this up with
one tool (verify_caller) and one gate (require) - see IDNV_PATTERN.md.

The ID&V phone number is only used to find the record, so it is never read
back: a misheard digit shows up as a miss, and the retry asks for it again.
The number the caller is calling from is never said either; the caller is
asked whether it's the one on their account, and a yes uses it.

State lives in conv.state.idnv (a dict), so it survives across turns and flows.
Nothing here ever returns the account holder's details to the model before the
caller is verified, and a failure never says which detail was wrong (strict).

Copy this file unchanged into a template's functions/ folder. Per-template
choices (which lookup to call, what to say on success, where the fail path
transfers to, the caller-ID question's wording) belong in the template's
verify_caller tool, not here.
"""

from _gen import *  # <AUTO GENERATED>
import re
from dataclasses import dataclass, field
from datetime import datetime


LAX = "lax"
STRICT = "strict"

# Limits. A template may pass its own to verify_lax / verify_strict.
MAX_MISMATCHES = 2  # identity checks that fail before the fail path
MAX_NOT_FOUND = 2  # phone numbers with no account before the fail path (lax)
MAX_UNCLEAR = 3  # unusable phone numbers (too short, garbled) before the fail path

VERIFY_FLOW = "verify_caller"
VERIFY_TOOL = "verify_caller"

# The default caller-ID question. A template passes its own wording as
# caller_id_question to require / verify_lax / verify_strict.
CALLER_ID_QUESTION = "Is the number you're calling from the one on your account?"
NOT_FOUND_QUESTION = "Could you say it again for me, or is it under a different one?"
MISMATCH_LINE = (
    "I'm sorry, those details don't match what we have. Could you say the phone number on "
    "your account again for me, or is it under a different one?"
)

# Every return that needs another answer from the caller ends with this, so the
# model passes the next answer to the tool (Dialog-RSN-1 won't repeat a lookup
# on its own after a miss).
CALL_AGAIN = f"Then call {VERIFY_TOOL} again with whatever they say, even if it's the same as before."
# How a yes to a question about a number reaches the tool. An acknowledgement
# answers the question, so it counts as agreement.
YES_TO_NUMBER = (
    'A yes or an acknowledgement ("okay", "sure", "yeah") means it is: pass '
    "phone_confirmed='true' and no phone number."
)


def _again(say: str, label: str = "", attempt: int = 0, limit: int = 0) -> str:
    head = f"{label} (attempt {attempt} of {limit}): " if label else ""
    return f"{head}{say} {CALL_AGAIN}"


FAILED_REASON_MISMATCH = "IDNV_FAILED"
FAILED_REASON_NOT_FOUND = "IDNV_ACCOUNT_NOT_FOUND"
FAILED_REASON_UNCLEAR = "IDNV_PHONE_NOT_CAPTURED"
FAILED_REASON_DECLINED = "IDNV_DECLINED"


@func_description("[UTIL] Caller ID&V helpers, not callable directly")
def idnv(conv: Conversation):
    return "ID&V utility module."


# --- Result -----------------------------------------------------------------


@dataclass
class Result:
    """What happened, and what the agent should do next.

    outcome:
      verified   the caller is verified (customer holds the matched record)
      need       something is still missing (see missing); `say` asks for it
      retry      a check failed but attempts remain; `say` asks again
      read_back  the member ID is read back before the final check (only with
                 read_back_member_id); `say` gives the readback
      wait       called again in the turn a question was asked, before the
                 caller answered: speak `utterance` and end the turn
      failed     limits reached or the caller can't/won't verify; transfer
    """

    outcome: str
    say: str = ""
    missing: list = field(default_factory=list)
    customer: dict | None = None
    handoff_reason: str = ""
    utterance: str = ""

    @property
    def verified(self) -> bool:
        return self.outcome == "verified"

    @property
    def failed(self) -> bool:
        return self.outcome == "failed"


# --- State ------------------------------------------------------------------


def _fresh() -> dict:
    return {
        "status": "unverified",  # unverified | verified | failed
        "strength": "",
        "method": "",
        "customer": None,
        "phone": "",
        "name": "",
        "dob": "",
        "member_id": "",
        "mismatches": 0,
        "not_found": 0,
        "unclear": 0,
        "missed_numbers": [],
        "caller_id": "",  # usable caller ID, never returned to the model
        "caller_id_matches": None,  # records on the caller ID, from match_ani
        "caller_id_offered": False,
        "pending": "",  # what a yes about a number means: caller_id | previous
        "previous_phone": "",  # the number before a miss, for "it's the same one"
        "question": "",  # the last question a yes answers (spoken again on wait)
        "question_turn": None,
        "id_read_back": "",
        "resume": "",
    }


def state(conv) -> dict:
    current = conv.state.idnv
    if not isinstance(current, dict):
        current = _fresh()
        conv.state.idnv = current
    for key, value in _fresh().items():
        current.setdefault(key, value)
    return current


def _save(conv, s: dict) -> None:
    conv.state.idnv = s


def is_verified(conv, strength: str = LAX) -> bool:
    s = state(conv)
    if s["status"] != "verified":
        return False
    return strength == LAX or s["strength"] == STRICT


def has_failed(conv) -> bool:
    return state(conv)["status"] == "failed"


def customer(conv) -> dict | None:
    """The verified account holder's record, or None."""
    s = state(conv)
    return s["customer"] if s["status"] == "verified" else None


# --- Normalisers ------------------------------------------------------------

_DIGIT_WORDS = {
    "zero": "0",
    "oh": "0",
    "o": "0",
    "one": "1",
    "won": "1",
    "two": "2",
    "to": "2",
    "too": "2",
    "three": "3",
    "four": "4",
    "for": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "ate": "8",
    "nine": "9",
}
_REPEAT = {"double": 2, "triple": 3}


def spoken_digits_to_string(value) -> str:
    """'two zero one, double five' -> '20155'. Digits pass through untouched."""
    text = str(value or "").lower()
    out, repeat = [], 1
    for token in re.findall(r"[a-z]+|\d", text):
        if token in _REPEAT:
            repeat = _REPEAT[token]
            continue
        digit = token if token.isdigit() else _DIGIT_WORDS.get(token)
        if digit is None:
            repeat = 1
            continue
        out.append(digit * repeat)
        repeat = 1
    return "".join(out)


def normalize_phone(value) -> str:
    """Ten-digit US number from digits or spoken words; '' if nothing usable."""
    digits = spoken_digits_to_string(value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def is_valid_phone(digits: str) -> bool:
    return len(digits) == 10 and digits[0] not in "01"


_NAME_NOISE = {"mr", "mrs", "ms", "miss", "dr", "jr", "sr", "ii", "iii", "iv"}


def _name_tokens(value) -> list[str]:
    words = re.findall(r"[a-z]+", str(value or "").lower().replace("'", ""))
    return [w for w in words if w not in _NAME_NOISE]


def _similarity(a: str, b: str) -> float:
    """1 - normalised Levenshtein distance."""
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return 1 - prev[-1] / max(len(a), len(b))


def name_matches(said: str, first_name: str, last_name: str) -> bool:
    """The surname must match (allowing for transcription slips); a first name,
    if given, must match too. 'Smith', 'John Smith' and 'Jon Smyth' all match
    John Smith; 'John Smithers' and 'Jane Smith' do not."""
    tokens = _name_tokens(said)
    last = "".join(_name_tokens(last_name))
    first = "".join(_name_tokens(first_name))
    if not tokens or not last:
        return False
    surname_ok = (
        _similarity(tokens[-1], last) >= 0.75
        or _similarity("".join(tokens), last) >= 0.75
    )
    if not surname_ok:
        return False
    if len(tokens) == 1 or not first:
        return True
    return _similarity(tokens[0], first) >= 0.75


_DOB_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%d %B %Y",
    "%B %d %Y",
    "%d %b %Y",
    "%b %d %Y",
)


def normalize_dob(value) -> str:
    """Date of birth as YYYY-MM-DD; '' if it is not a full, plausible date."""
    text = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", str(value or "").strip(), flags=re.I)
    text = re.sub(r"\s+", " ", text.replace(",", " ")).strip()
    for fmt in _DOB_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if 1900 <= parsed.year <= datetime.now().year:
            return parsed.strftime("%Y-%m-%d")
    return ""


def normalize_id(value) -> str:
    """Member/account IDs compare on letters and digits only, case-insensitive."""
    return re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()


_WORDS = "zero one two three four five six seven eight nine".split()


def spell_phone(digits: str) -> str:
    """'2015550123' -> 'two zero one, five five five, zero one two three'."""
    groups = [digits[:3], digits[3:6], digits[6:]] if len(digits) == 10 else [digits]
    return ", ".join(" ".join(_WORDS[int(d)] for d in g) for g in groups if g)


def spell_id(value) -> str:
    """'58204452' -> 'five eight two zero, four four five two'. Groups of four;
    letters are said as letters."""
    chars = normalize_id(value)
    groups = [chars[i : i + 4] for i in range(0, len(chars), 4)]
    return ", ".join(
        " ".join(_WORDS[int(c)] if c.isdigit() else c for c in g) for g in groups
    )


# --- Caller ID --------------------------------------------------------------


def _caller_id(conv, s) -> str:
    """The usable caller ID as ten digits, or ''. Never returned to the model."""
    if s.get("caller_id"):
        return s["caller_id"]
    digits = normalize_phone(getattr(conv, "caller_number", "") or "")
    return digits if is_valid_phone(digits) else ""


def match_ani(conv, caller_number, lookup) -> bool:
    """Lax verification from the caller ID alone. Call once from start_function.

    Verifies only when the number is a valid US number with exactly one account
    on it; a shared number (several accounts) still needs a name, and the caller
    is asked whether the number they're calling from is the one on the account.
    """
    s = state(conv)
    digits = normalize_phone(caller_number)
    if not is_valid_phone(digits):
        return False
    s["caller_id"] = digits
    _save(conv, s)
    try:
        customers = lookup(digits) or []
    except Exception as e:  # a lookup failure must never break call start
        conv.log.warning("ID&V caller ID lookup failed", error=str(e))
        return False
    s["caller_id_matches"] = len(customers)
    _save(conv, s)
    if len(customers) != 1:
        return False
    s.update(status="verified", strength=LAX, method="caller_id", customer=customers[0])
    s["phone"] = digits
    _save(conv, s)
    conv.write_metric("IDNV_SUCCESS", "caller_id")
    return True


def _offers_caller_id(conv, s, strength: str) -> bool:
    """Whether to ask if the number they're calling from is the one on the
    account: a usable caller ID, not asked yet, no phone number given. Lax asks
    only when the caller ID matched records (one record already verified at call
    start); strict asks whenever the caller ID is usable, since the date of
    birth and ID must still match."""
    if s["phone"] or s["caller_id_offered"] or not _caller_id(conv, s):
        return False
    return strength == STRICT or bool(s.get("caller_id_matches"))


def _ask_caller_id(conv, s, question: str) -> str:
    question = question or CALLER_ID_QUESTION
    s.update(caller_id_offered=True, pending="caller_id")
    _asked(conv, s, question)
    return _again(
        f'Ask: "{question}" Never say the number. {YES_TO_NUMBER} If they give another number, '
        "pass that. If they say no, ask for the phone number on their account."
    )


# --- Same-turn guard --------------------------------------------------------


def _turn(conv):
    """The history's length, used only as a same-turn marker (the history at tool
    time holds earlier turns, so it grows once the caller has replied). None if
    the platform doesn't expose it."""
    try:
        return len(conv.history)
    except Exception:
        return None


def _asked(conv, s, question: str) -> None:
    """Remember the question a yes would answer, and the turn it was asked in."""
    s.update(question=question, question_turn=_turn(conv))
    _save(conv, s)


def _same_turn(conv, s) -> bool:
    turn = _turn(conv)
    return turn is not None and turn == s.get("question_turn")


def _wait(s, missing: list) -> Result:
    """Called again in the turn a question was asked: the caller hasn't answered.
    Nothing is counted or confirmed; the template speaks `utterance`."""
    return Result(
        "wait",
        missing=missing,
        say=(
            f'WAIT for the caller\'s answer to "{s["question"]}" before calling {VERIFY_TOOL} '
            "again."
        ),
        utterance=s["question"],
    )


# --- Verification -----------------------------------------------------------


def _fail(conv, s, reason: str) -> Result:
    s["status"] = "failed"
    _save(conv, s)
    conv.write_metric("IDNV_FAILED", reason)
    return Result("failed", handoff_reason=reason)


def _verified(conv, s, record: dict, strength: str, method: str) -> Result:
    s.update(status="verified", strength=strength, method=method, customer=record)
    _save(conv, s)
    conv.write_metric("IDNV_SUCCESS", method)
    return Result("verified", customer=record)


def _take_phone(conv, s, phone, max_unclear: int, agreed: bool) -> Result | None:
    """Store a newly given phone number. Returns a Result when the caller has to
    be asked again (or the limit is hit), None otherwise.

    With no number given, a yes (agreed) to the pending question uses the caller
    ID or the number given before; it is never read back."""
    if not str(phone or "").strip():
        if not s["pending"]:
            return None
        if _same_turn(conv, s):
            return _wait(s, ["phone"])
        if agreed:
            number = (
                _caller_id(conv, s)
                if s["pending"] == "caller_id"
                else s["previous_phone"]
            )
            s.update(phone=number, pending="")
        elif s["pending"] == "caller_id":
            s["pending"] = ""  # not the number they're calling from
        _save(conv, s)
        return None
    digits = normalize_phone(phone)
    if not digits:
        # Words with no digits ("the number is...") are not an attempt.
        return Result(
            "need",
            missing=["phone"],
            say=_again('Say "Go ahead" and wait for the number.'),
        )
    if not is_valid_phone(digits):
        s["unclear"] += 1
        _save(conv, s)
        if s["unclear"] >= max_unclear:
            return _fail(conv, s, FAILED_REASON_UNCLEAR)
        return Result(
            "retry",
            missing=["phone"],
            say=_again(
                "That wasn't a full phone number. Say: \"Sorry, I didn't catch all of that. "
                'Could you say the full number again for me?" Never repeat the digits they said.',
                "NOT A FULL NUMBER",
                s["unclear"],
                max_unclear,
            ),
        )
    s.update(phone=digits, pending="")
    _save(conv, s)
    return None


def _lookup(conv, s, lookup) -> list[dict]:
    try:
        return list(lookup(s["phone"]) or [])
    except Exception as e:
        conv.log.error("ID&V lookup failed", error=str(e))
        raise


def _not_found(conv, s, max_not_found: int) -> Result:
    """No account on this number (lax): counted, and the caller is asked to say
    it again or give another. The number is never read back."""
    s["not_found"] += 1
    missed = s.get("missed_numbers", [])
    s["missed_numbers"] = missed + ([s["phone"]] if s["phone"] not in missed else [])
    s.update(previous_phone=s["phone"], phone="", pending="previous")
    _save(conv, s)
    if s["not_found"] >= max_not_found:
        return _fail(conv, s, FAILED_REASON_NOT_FOUND)
    _asked(conv, s, NOT_FOUND_QUESTION)
    return Result(
        "retry",
        missing=["phone"],
        say=_again(
            "Nothing is under that number. Say you can't find one under that number, then ask: "
            f'"{NOT_FOUND_QUESTION}" Never read the number back. If they say it\'s the same '
            "number, pass phone_confirmed='true' and no phone number. If they say there isn't "
            f"another one, call {VERIFY_TOOL} with caller_cannot_verify='true'.",
            "NO ACCOUNT",
            s["not_found"],
            max_not_found,
        ),
    )


def verify_lax(
    conv,
    phone,
    name,
    lookup,
    caller_cannot_verify: bool = False,
    max_mismatches: int = MAX_MISMATCHES,
    max_not_found: int = MAX_NOT_FOUND,
    max_unclear: int = MAX_UNCLEAR,
    phone_confirmed: bool = False,
    caller_id_question: str = "",
) -> Result:
    """Phone number on the account + the account holder's name.

    Call with whatever the caller has given so far; empty strings for the rest.
    lookup(phone_digits) -> list of records with first_name and last_name.
    phone_confirmed: the caller said yes (or "okay") to the number the last
    return asked about - the number they're calling from, or the same one again.
    """
    s = state(conv)
    if s["status"] == "verified":
        return Result("verified", customer=s["customer"])
    if s["status"] == "failed":
        return Result("failed", handoff_reason=FAILED_REASON_MISMATCH)
    if caller_cannot_verify:
        # After a number with no account, "there's no other number" means not found.
        return _fail(
            conv,
            s,
            FAILED_REASON_NOT_FOUND if s["not_found"] else FAILED_REASON_DECLINED,
        )

    if str(name or "").strip():
        s["name"] = str(name).strip()
        _save(conv, s)
    retry = _take_phone(conv, s, phone, max_unclear, phone_confirmed)
    if retry:
        return retry

    if not s["phone"]:
        missing = ["phone"] + ([] if s["name"] else ["name"])
        if _offers_caller_id(conv, s, LAX):
            return Result(
                "need", missing=missing, say=_ask_caller_id(conv, s, caller_id_question)
            )
        return Result(
            "need",
            missing=missing,
            say=_again(
                "Ask for the phone number on their account, starting with the area code."
            ),
        )
    customers = _lookup(conv, s, lookup)
    if not customers:
        return _not_found(conv, s, max_not_found)
    if not s["name"]:
        return Result(
            "need",
            missing=["name"],
            say=_again(
                "Ask for the full name on the account. Don't say whether you found an account "
                "or whose it is."
            ),
        )

    match = next(
        (
            c
            for c in customers
            if name_matches(s["name"], c.get("first_name"), c.get("last_name"))
        ),
        None,
    )
    if match:
        return _verified(conv, s, match, LAX, "phone_and_name")

    s["mismatches"] += 1
    s["name"] = ""
    _save(conv, s)
    if s["mismatches"] >= max_mismatches:
        return _fail(conv, s, FAILED_REASON_MISMATCH)
    return Result(
        "retry",
        missing=["name"],
        say=_again(
            "That name doesn't match the account on that number. Kept: the phone number, so "
            "don't ask for it again. Ask again for: the full name the account is under, and "
            "pass only the name they give now. Never say or hint at the name on file.",
            "NOT VERIFIED",
            s["mismatches"],
            max_mismatches,
        ),
    )


def _member_id_read_back(conv, s, agreed: bool) -> Result | None:
    """Before the final strict check (read_back_member_id only): read the member
    ID back. A yes or an acknowledgement confirms it (None: go on to the check);
    a corrected ID is read back in turn."""
    if s["id_read_back"] != s["member_id"]:
        s["id_read_back"] = s["member_id"]
        _asked(conv, s, f"Just to check, that's {spell_id(s['member_id'])}?")
    elif _same_turn(conv, s):
        return _wait(s, ["member_id"])
    elif agreed:
        return None
    else:
        _asked(conv, s, s["question"])
    return Result(
        "read_back",
        missing=["member_id"],
        say=(
            f'Read the member ID back: "{s["question"]}" Then wait for their answer. A yes or an '
            'acknowledgement ("okay", "sure", "yeah") confirms it: call '
            f"{VERIFY_TOOL} again with member_id_confirmed='true'. If they correct it, call "
            f"{VERIFY_TOOL} again with the corrected member ID."
        ),
    )


def verify_strict(
    conv,
    phone,
    date_of_birth,
    member_id,
    lookup,
    caller_cannot_verify: bool = False,
    max_mismatches: int = MAX_MISMATCHES,
    max_not_found: int = MAX_NOT_FOUND,
    max_unclear: int = MAX_UNCLEAR,
    phone_confirmed: bool = False,
    caller_id_question: str = "",
    read_back_member_id: bool = False,
    member_id_confirmed: bool = False,
) -> Result:
    """Phone number + date of birth + member/account ID, all on one record.

    lookup(phone_digits) -> list of records with dob (YYYY-MM-DD) and member_id.
    A failed check (a number with no account included) never says which detail
    was wrong, and clears all three, so the retry asks for the phone number,
    then the date of birth and ID.
    phone_confirmed: the caller said yes (or "okay") to the number the last
    return asked about - the number they're calling from, or the same one again.
    read_back_member_id: read the member ID back before the final check, where a
    miss means the fail path; member_id_confirmed is the caller's yes to it.
    max_not_found is unused (a number with no account is a mismatch); it is kept
    so both verify functions take the same limits.
    """
    s = state(conv)
    if is_verified(conv, STRICT):
        return Result("verified", customer=s["customer"])
    if s["status"] == "failed":
        return Result("failed", handoff_reason=FAILED_REASON_MISMATCH)
    if caller_cannot_verify:
        return _fail(
            conv,
            s,
            FAILED_REASON_NOT_FOUND if s["not_found"] else FAILED_REASON_DECLINED,
        )

    bad_dob = False
    if str(date_of_birth or "").strip():
        dob = normalize_dob(date_of_birth)
        bad_dob = not dob
        if dob:
            s["dob"] = dob
    if str(member_id or "").strip():
        s["member_id"] = normalize_id(member_id)
    _save(conv, s)
    retry = _take_phone(conv, s, phone, max_unclear, phone_confirmed)
    if retry:
        return retry
    if bad_dob:
        return Result(
            "retry",
            missing=["date_of_birth"],
            say=_again("Ask for their full date of birth: day, month and year."),
        )

    missing = [
        k
        for k, v in (
            ("phone", s["phone"]),
            ("date_of_birth", s["dob"]),
            ("member_id", s["member_id"]),
        )
        if not v
    ]
    if missing:
        if missing[0] == "phone" and _offers_caller_id(conv, s, STRICT):
            return Result(
                "need", missing=missing, say=_ask_caller_id(conv, s, caller_id_question)
            )
        labels = {
            "phone": "the phone number on their account",
            "date_of_birth": "their date of birth",
            "member_id": "their member ID",
        }
        return Result(
            "need",
            missing=missing,
            say=_again(f"Ask for {labels[missing[0]]}. Ask for one thing at a time."),
        )

    if read_back_member_id and s["mismatches"] + 1 >= max_mismatches:
        read_back = _member_id_read_back(conv, s, member_id_confirmed)
        if read_back:
            return read_back

    customers = _lookup(conv, s, lookup)
    record = next(
        (
            c
            for c in customers
            if normalize_dob(c.get("dob")) == s["dob"]
            and normalize_id(c.get("member_id")) == s["member_id"]
        ),
        None,
    )
    if record:
        return _verified(conv, s, record, STRICT, "phone_dob_member_id")

    # No account on the number and a wrong detail get the same reply, so it
    # never hints at which detail failed or whether there's an account.
    s["mismatches"] += 1
    s.update(
        previous_phone=s["phone"],
        phone="",
        dob="",
        member_id="",
        id_read_back="",
        pending="previous",
    )
    _save(conv, s)
    if s["mismatches"] >= max_mismatches:
        return _fail(conv, s, FAILED_REASON_MISMATCH)
    _asked(conv, s, MISMATCH_LINE)
    return Result(
        "retry",
        missing=["phone", "date_of_birth", "member_id"],
        say=_again(
            "Those details don't match our records; never say which one, or whether there's an "
            f'account on the number. Say: "{MISMATCH_LINE}" Then ask again for their date of '
            "birth, then their member ID, one at a time. Never read the number back. If they say "
            "it's the same number, pass phone_confirmed='true' and no phone number. Pass only "
            "what they say from now on, never the details they gave before.",
            "NOT VERIFIED",
            s["mismatches"],
            max_mismatches,
        ),
    )


# --- Gate -------------------------------------------------------------------


def require(
    conv,
    resume: str,
    strength: str = LAX,
    verify_flow: str = VERIFY_FLOW,
    caller_id_question: str = "",
):
    """Gate for a task: call it first in the task flow's entry function step (or
    in a global tool, for a task with no flow).

    Returns None when the caller is verified to `strength`, so the task carries
    on. Otherwise sends the caller to the verification flow, remembers what to
    resume afterwards (a flow name, or any key the template's verify_caller
    tool knows), and returns the instruction for the agent's next reply.
    """
    if is_verified(conv, strength):
        return None
    s = state(conv)
    s["resume"] = resume
    _save(conv, s)
    conv.goto_flow(verify_flow)
    head = (
        "Before you can help with this you need to confirm who the caller is. If they already "
        f"gave their phone number or name, call {VERIFY_TOOL} with them now; otherwise "
    )
    if _offers_caller_id(conv, s, strength):
        ask = _ask_caller_id(conv, s, caller_id_question)
        return f"{head}{ask[0].lower()}{ask[1:]}"
    return f"{head}ask for the phone number on their account."


def take_resume(conv) -> str:
    """What to resume after verification (and forget it)."""
    s = state(conv)
    target = s.get("resume") or ""
    s["resume"] = ""
    _save(conv, s)
    return target


def state_line(conv) -> str:
    """One line for the call-state block. Never includes the account holder's details
    before verification."""
    s = state(conv)
    if s["status"] == "verified":
        first = (s["customer"] or {}).get("first_name", "")
        return (
            f"Identity: verified ({s['method'].replace('_', ' ')}), caller is {first}"
        )
    if s["status"] == "failed":
        return "Identity: could not be verified"
    have = [
        label
        for label, key in (
            ("phone", "phone"),
            ("name", "name"),
            ("date of birth", "dob"),
            ("member ID", "member_id"),
        )
        if s.get(key)
    ]
    return "Identity: not verified yet" + (
        f" (have: {', '.join(have)})" if have else ""
    )
