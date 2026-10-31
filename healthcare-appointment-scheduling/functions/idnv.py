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

State lives in conv.state.idnv (a dict), so it survives across turns and flows.
Nothing here ever returns the account holder's details to the model before the
caller is verified, and a failure never says which detail was wrong (strict).

Copy this file unchanged into a template's functions/ folder. Per-template
choices (which lookup to call, what to say on success, where the fail path
transfers to) belong in the template's verify_caller tool, not here.
"""

from _gen import *  # <AUTO GENERATED>
import re
from dataclasses import dataclass, field
from datetime import datetime


LAX = "lax"
STRICT = "strict"

# Limits. A template may pass its own to verify_lax / verify_strict.
MAX_MISMATCHES = 2  # identity checks that fail before the fail path
MAX_NOT_FOUND = 2  # confirmed phone numbers with no account before the fail path
MAX_UNCLEAR = 3  # unusable phone numbers (too short, garbled) before the fail path
MAX_UNCONFIRMED = (
    2  # readbacks the caller doesn't confirm or correct before the fail path
)

VERIFY_FLOW = "verify_caller"
VERIFY_TOOL = "verify_caller"

# Every return that needs another answer from the caller ends with this, so the
# model passes the next answer to the tool (Dialog-RSN-1 won't repeat a lookup
# on its own after a miss).
CALL_AGAIN = f"Then call {VERIFY_TOOL} again with whatever they say, even if it's the same as before."


def _again(say: str, label: str = "", attempt: int = 0, limit: int = 0) -> str:
    head = f"{label} (attempt {attempt} of {limit}): " if label else ""
    return f"{head}{say} {CALL_AGAIN}"


def _confirm_phone(phone: str, label: str = "") -> str:
    """The phone readback. Like a write tool's readback, only an explicit
    phone_confirmed='true' (a clear yes to this number) confirms it."""
    head = f"{label}: " if label else ""
    return (
        f'{head}Read the phone number back exactly as "{spell_phone(phone)}" and ask if '
        "that's right, then wait for the caller's answer. Only after they reply, call "
        f"{VERIFY_TOOL} again with whatever they said: phone_confirmed='true' only if they "
        'clearly said yes or repeated the same number (an "okay" or anything unclear is not '
        "a yes); if they corrected it, pass the corrected number with phone_confirmed='false'."
    )


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
      read_back  no account on this number yet: read the number back first
      retry      a check failed but attempts remain; `say` asks again
      failed     limits reached or the caller can't/won't verify; transfer
    """

    outcome: str
    say: str = ""
    missing: list = field(default_factory=list)
    customer: dict | None = None
    handoff_reason: str = ""

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
        "phone_read_back": False,
        "phone_confirmed": False,
        "name": "",
        "dob": "",
        "member_id": "",
        "mismatches": 0,
        "not_found": 0,
        "unclear": 0,
        "unconfirmed": 0,
        "missed_numbers": [],
        "readback_turn": None,
        "resume": "",
    }


def state(conv) -> dict:
    current = conv.state.idnv
    if not isinstance(current, dict):
        current = _fresh()
        conv.state.idnv = current
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


def spell_phone(digits: str) -> str:
    """'2015550123' -> 'two zero one, five five five, zero one two three'."""
    words = "zero one two three four five six seven eight nine".split()
    groups = [digits[:3], digits[3:6], digits[6:]] if len(digits) == 10 else [digits]
    return ", ".join(" ".join(words[int(d)] for d in g) for g in groups if g)


# --- Caller ID --------------------------------------------------------------


def match_ani(conv, caller_number, lookup) -> bool:
    """Lax verification from the caller ID alone. Call once from start_function.

    Verifies only when the number is a valid US number with exactly one account
    on it; a shared number (several accounts) still needs a name.
    """
    s = state(conv)
    digits = normalize_phone(caller_number)
    if not is_valid_phone(digits):
        return False
    try:
        customers = lookup(digits) or []
    except Exception as e:  # a lookup failure must never break call start
        conv.log.warning("ID&V caller ID lookup failed", error=str(e))
        return False
    if len(customers) != 1:
        return False
    s.update(status="verified", strength=LAX, method="caller_id", customer=customers[0])
    s["phone"] = digits
    _save(conv, s)
    conv.write_metric("IDNV_SUCCESS", "caller_id")
    return True


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


def _take_phone(
    conv, s, phone, max_unclear: int, phone_confirmed: bool
) -> Result | None:
    """Store a newly given phone number. Returns a Result when the caller has to
    be asked again (or the limit is hit), None when the number is usable.

    A number read back is confirmed only by phone_confirmed=True, with the same
    number or none; a different number replaces it and is read back in turn."""
    if not str(phone or "").strip():
        if (
            s["phone_read_back"]
            and not s["phone_confirmed"]
            and phone_confirmed
            and not _same_turn_as_readback(conv, s)
        ):
            s["phone_confirmed"] = True
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
                "That wasn't a full phone number. Ask for the ten-digit number on their account, "
                "starting with the area code.",
                "NOT A FULL NUMBER",
                s["unclear"],
                max_unclear,
            ),
        )
    if digits != s["phone"] and digits in s.get("missed_numbers", []):
        # A number already read back, confirmed and found to have no account:
        # the caller is standing by it again, so don't read it back a second time.
        s.update(phone=digits, phone_read_back=True, phone_confirmed=True)
    elif digits != s["phone"]:
        s.update(
            phone=digits, phone_read_back=False, phone_confirmed=False, unconfirmed=0
        )
    elif (
        s["phone_read_back"] and phone_confirmed and not _same_turn_as_readback(conv, s)
    ):
        s["phone_confirmed"] = True
    _save(conv, s)
    return None


def _turn(conv):
    """The history's length, used only as a same-turn marker (the history at tool
    time holds earlier turns, so it grows once the caller has replied). None if
    the platform doesn't expose it."""
    try:
        return len(conv.history)
    except Exception:
        return None


def _same_turn_as_readback(conv, s) -> bool:
    turn = _turn(conv)
    return turn is not None and turn == s.get("readback_turn")


def _read_back(conv, s, label: str = "") -> Result:
    s["readback_turn"] = _turn(conv)
    _save(conv, s)
    return Result("read_back", missing=["phone"], say=_confirm_phone(s["phone"], label))


def _not_confirmed(conv, s, max_unconfirmed: int) -> Result:
    """The caller neither confirmed nor corrected the read-back number. Counted,
    so a caller who keeps saying "okay" reaches the fail path instead of a loop.
    A call in the same turn as the readback (the caller hasn't answered yet) is
    not counted: the model is told to wait."""
    if _same_turn_as_readback(conv, s):
        return Result(
            "read_back",
            missing=["phone"],
            say=(
                f'WAIT: you have just asked the caller to confirm "{spell_phone(s["phone"])}". '
                f"Wait for their answer; don't call {VERIFY_TOOL} again until they reply."
            ),
        )
    s["unconfirmed"] = s.get("unconfirmed", 0) + 1
    _save(conv, s)
    if s["unconfirmed"] >= max_unconfirmed:
        return _fail(conv, s, FAILED_REASON_UNCLEAR)
    label = f"NOT CONFIRMED YET (attempt {s['unconfirmed']} of {max_unconfirmed})"
    return _read_back(conv, s, label)


def _lookup(conv, s, lookup) -> list[dict]:
    try:
        return list(lookup(s["phone"]) or [])
    except Exception as e:
        conv.log.error("ID&V lookup failed", error=str(e))
        raise


def _not_found(conv, s, max_not_found: int, max_unconfirmed: int) -> Result:
    """No account on this number. First time for a number: read it back, since
    a misheard digit is the likeliest cause. If the caller stands by it, count
    a miss and ask whether the account is under another number."""
    if not s["phone_read_back"]:
        s["phone_read_back"] = True
        s["phone_confirmed"] = False
        return _read_back(conv, s)
    if not s["phone_confirmed"]:
        return _not_confirmed(conv, s, max_unconfirmed)
    s["not_found"] += 1
    missed = s.get("missed_numbers", [])
    s["missed_numbers"] = missed + ([s["phone"]] if s["phone"] not in missed else [])
    s.update(phone="", phone_read_back=False, phone_confirmed=False, unconfirmed=0)
    _save(conv, s)
    if s["not_found"] >= max_not_found:
        return _fail(conv, s, FAILED_REASON_NOT_FOUND)
    return Result(
        "retry",
        missing=["phone"],
        say=_again(
            "There's no account under that number. Ask if the account could be under a "
            "different phone number. If they say there isn't another one, call verify_caller "
            "with caller_cannot_verify='true'.",
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
    max_unconfirmed: int = MAX_UNCONFIRMED,
) -> Result:
    """Phone number on the account + the account holder's name.

    Call with whatever the caller has given so far; empty strings for the rest.
    lookup(phone_digits) -> list of records with first_name and last_name.
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

    retry = _take_phone(conv, s, phone, max_unclear, phone_confirmed)
    if retry:
        return retry
    if str(name or "").strip():
        s["name"] = str(name).strip()
        _save(conv, s)

    if not s["phone"]:
        return Result(
            "need",
            missing=["phone"] + ([] if s["name"] else ["name"]),
            say=_again(
                "Ask for the phone number on their account, starting with the area code."
            ),
        )
    customers = _lookup(conv, s, lookup)
    if not customers:
        return _not_found(conv, s, max_not_found, max_unconfirmed)
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
    max_unconfirmed: int = MAX_UNCONFIRMED,
) -> Result:
    """Phone number + date of birth + member/account ID, all on one record.

    lookup(phone_digits) -> list of records with dob (YYYY-MM-DD) and member_id.
    A failed check never says which detail was wrong, and clears the date of
    birth and ID so both are asked again.
    """
    s = state(conv)
    if is_verified(conv, STRICT):
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

    retry = _take_phone(conv, s, phone, max_unclear, phone_confirmed)
    if retry:
        return retry
    if str(date_of_birth or "").strip():
        dob = normalize_dob(date_of_birth)
        if not dob:
            return Result(
                "retry",
                missing=["date_of_birth"],
                say=_again("Ask for their full date of birth: day, month and year."),
            )
        s["dob"] = dob
    if str(member_id or "").strip():
        s["member_id"] = normalize_id(member_id)
    _save(conv, s)

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

    customers = _lookup(conv, s, lookup)
    if not customers:
        # A phone readback guards against a misheard digit, as in lax, but the
        # caller is never told that no account exists on the number.
        if not s["phone_read_back"]:
            s["phone_read_back"] = True
            s["phone_confirmed"] = False
            return _read_back(conv, s)
        if not s["phone_confirmed"]:
            return _not_confirmed(conv, s, max_unconfirmed)
        record = None
    else:
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

    # The phone number is kept whether or not it found an account, so the next
    # question is the same either way and never hints at which detail failed.
    s["mismatches"] += 1
    s.update(dob="", member_id="")
    _save(conv, s)
    if s["mismatches"] >= max_mismatches:
        return _fail(conv, s, FAILED_REASON_MISMATCH)
    return Result(
        "retry",
        missing=["date_of_birth", "member_id"],
        say=_again(
            "Those details don't match our records; never say which one. Kept: the phone "
            "number, so don't ask for it again and pass phone_number as an empty string. Ask "
            "again for: their date of birth, then their member ID, one at a time. Pass only "
            "what they say from now on, never the date of birth or ID they gave before.",
            "NOT VERIFIED",
            s["mismatches"],
            max_mismatches,
        ),
    )


# --- Gate -------------------------------------------------------------------


def require(conv, resume: str, strength: str = LAX, verify_flow: str = VERIFY_FLOW):
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
    return (
        "Before you can help with this you need to confirm who the caller is. If they already "
        "gave their phone number or name, call verify_caller with them now; otherwise ask for "
        "the phone number on their account."
    )


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
