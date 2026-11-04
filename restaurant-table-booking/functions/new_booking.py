"""A new booking's details, what to ask next, and the readback, shared by the three
Make Booking tools.

The order the design asks in: day and time, party size, availability, name,
number (the caller-ID offer when there's a usable caller ID), one note question,
then the readback. Anything the caller has already said is used and not asked
again. The readback names the party, day, time, name, a number the caller gave
(never the number they're calling from) and a note; after a correction, only
what changed.
"""

from _gen import *  # <AUTO GENERATED>
from functions import bookings, idnv
from functions.handoff import handoff

READBACK_KEY = "new_booking"
CALLER_ID_KEY = "booking_caller_id"
BOOK_QUESTION = "Shall I go ahead and book that?"
ASK_AGAIN = "Great. Shall I go ahead and book it, then?"
CALLER_ID_QUESTION = "Is the number you're calling from the best one to reach you on?"
NUMBER_QUESTION = "What's the best number to reach you on?"
NOTE_QUESTION = (
    "Is there anything we should know about, like allergies or a special occasion?"
)
MAX_UNCLEAR_PHONE = 3
NO_NOTE = ("na", "none", "no", "nothing", "no note", "nope", "n/a")


@func_description("[UTIL] New booking helpers, not callable directly")
def new_booking(conv: Conversation):
    return "New booking helpers module."


def booking_request(conv) -> dict:
    req = conv.state.booking_request
    if not isinstance(req, dict):
        req = {
            "party_size": 0,
            "date": "",
            "time": "",
            "name": "",
            "phone": "",
            "phone_from_caller_id": False,
            "caller_id_declined": False,
            "notes": "",
            "notes_answered": False,
            "offer": None,  # the table held for the caller: {"date", "time"}
            "offered": [],  # free times the caller has been told about, "YYYY-MM-DDTHH:MM"
            "phone_unclear": 0,
        }
    return dict(req)


def save(conv, req: dict) -> None:
    conv.state.booking_request = req


def caller_id(conv) -> str:
    """The usable caller ID, or ''. Never given to the model."""
    number = idnv.normalize_phone(conv.state.caller_phone)
    return number if idnv.is_valid_phone(number) else ""


def missing_details(req: dict) -> list[str]:
    missing = []
    if not req["date"] and not req["time"]:
        missing.append('Ask: "What day and time were you thinking of?"')
    elif not req["date"]:
        missing.append("Ask what day they'd like.")
    elif not req["time"]:
        missing.append("Ask what time they'd like.")
    if not req["party_size"]:
        missing.append('Ask: "And how many people will it be for?"')
    return missing


def next_step(conv, req: dict, mark: bool = False) -> str:
    """The one thing to ask next, in the design's order. mark: this return asks it, so
    record the turn (a yes to the caller-ID question in the same turn isn't an answer)."""
    missing = missing_details(req)
    if missing and not req.get("offer"):
        return missing[0] + " Then call update_booking_request with the answer."
    if not req.get("offer"):
        return "Call update_booking_request with the day, time and party size."
    if not req["name"]:
        return 'Ask: "What name should I book it under?" Then call update_booking_details with it.'
    if not req["phone"]:
        if caller_id(conv) and not req["caller_id_declined"]:
            if mark:
                bookings.mark_asked(conv, CALLER_ID_KEY)
            return (
                f'Ask: "{CALLER_ID_QUESTION}" Never say the number. A yes, or an acknowledgement '
                '("okay", "yeah", "sure"): call update_booking_details with '
                "use_calling_number='true'. A no: call it with use_calling_number='false'. Another "
                "number: pass it as phone_number."
            )
        return f'Ask: "{NUMBER_QUESTION}" Then call update_booking_details with it.'
    if not req["notes_answered"]:
        return (
            f'Ask: "{NOTE_QUESTION}" Then call update_booking_details with what they say as '
            "notes, or notes='none' if there's nothing."
        )
    return (
        f'Wait for the answer to "{BOOK_QUESTION}" A yes, or an acknowledgement to it ("okay", '
        '"sure", "sounds good", "go on"), is a yes: call finalize_booking with '
        "caller_confirmed='true'."
    )


def fields(conv, req: dict) -> list[tuple[str, str]]:
    offer = req.get("offer") or {}
    out = [
        ("party", f"a table for {bookings.say_party(req['party_size'])}" if req["party_size"] else ""),
        ("when", bookings.when(conv, offer["date"], offer["time"]) if offer else ""),
        ("name", f"under {req['name']}" if req["name"] else ""),
        # The number they're calling from is never read out.
        ("number", "" if req["phone_from_caller_id"] or not req["phone"] else f"on {bookings.spell_phone(req['phone'])}"),
        ("notes", f"with a note: {req['notes']}" if req["notes"] else ""),
    ]  # fmt: skip
    return out


def sentence(values: dict) -> str:
    """'So that's a table for two tonight at 7:30, under Tom Baker. Shall I go ahead
    and book that?'"""
    parts = [v for k, v in values.items() if k in ("party", "when") and v]
    head = " ".join(parts)
    rest = [v for k, v in values.items() if k not in ("party", "when") and v]
    body = ", ".join([head, *rest] if head else rest)
    return f"So that's {body}. {BOOK_QUESTION}"


def full_sentence(conv, req: dict) -> str:
    return sentence({k: v for k, v in fields(conv, req) if v})


def readback(conv, req: dict, lead: str = "") -> str:
    """The readback the caller hears before the booking: everything the first time,
    then only what changed. Records the turn it's asked in."""
    changed, mode = bookings.readback_changes(conv, READBACK_KEY, fields(conv, req))
    bookings.mark_asked(conv, READBACK_KEY)
    after = (
        ' A yes, or an acknowledgement to that question ("okay", "sure", "sounds good", '
        "\"go on\"), is a yes: call finalize_booking with caller_confirmed='true'. A correction "
        "goes to the tool it belongs to. Real hesitation: answer or wait, then ask again."
    )
    if mode == "none":
        say = f'The caller has heard the details. Ask again: "{BOOK_QUESTION}"'
    elif mode == "changes":
        say = (
            "Read back only what changed, exactly as below and nothing more, in one sentence, then "
            "ask the question. If the caller's reply also changed something this doesn't name (a "
            "new number: call update_booking_request again with phone_number; a name or note: "
            "update_booking_details), call that first, before you say anything, and read back "
            "what it returns: "
            f'"{sentence(changed)}"'
        )
    else:
        say = (
            "Read the booking back in one sentence, then ask the question (the note can be said "
            f'in a few words): "{sentence(changed)}"'
        )
    return f"NOT BOOKED YET. {lead}{say}{after}\n\n{request_state(conv, req)}"


def request_state(conv, req: dict | None = None) -> str:
    req = req or booking_request(conv)
    offer = req.get("offer")
    contact = "not given"
    if req["phone"]:
        contact = (
            "the number they're calling from"
            if req["phone_from_caller_id"]
            else bookings.spell_phone(req["phone"])
        )
    lines = [
        "Task: book a table",
        "Party: " + (bookings.say_people(req["party_size"]) if req["party_size"] else "not given"),
        "Asked for: " + (" ".join(x for x in (req["date"], req["time"]) if x) or "nothing yet"),
        "Table held: " + (bookings.when(conv, offer["date"], offer["time"]) if offer else "none yet"),
        "Name: " + (req["name"] or "not given"),
        "Contact number: " + contact,
        "Note: " + (req["notes"] or ("none" if req["notes_answered"] else "not asked yet")),
    ]  # fmt: skip
    return bookings.call_state(conv, lines, next_step(conv, req))


def after_details(conv, req: dict, lead: str = "") -> str:
    """Once a table is held: the next question, or the readback when everything's in."""
    if req["name"] and req["phone"] and req["notes_answered"]:
        return readback(conv, req, lead)
    return f"{lead}{next_step(conv, req, mark=True)}\n\n{request_state(conv, req)}"


def take_phone(conv, req: dict, phone_number: str, tool: str):
    """Store a contact number the caller gave. Returns None when it's stored, or the
    return for an unusable one (counted; the third goes to the team)."""
    digits = idnv.normalize_phone(phone_number)
    if digits and idnv.is_valid_phone(digits):
        req["phone"], req["phone_from_caller_id"] = digits, False
        req["phone_unclear"] = 0
        return None
    if not digits:
        return None
    req["phone_unclear"] += 1
    save(conv, req)
    if req["phone_unclear"] >= MAX_UNCLEAR_PHONE:
        return handoff(
            conv,
            "BOOKING_PHONE_NOT_CAPTURED",
            "I'm sorry, I'm having trouble getting your number. Let me put you through to the "
            "team to finish the booking. One moment, please.",
        )
    return (
        f"NOT A FULL NUMBER (attempt {req['phone_unclear']} of {MAX_UNCLEAR_PHONE}): say "
        '"Sorry, I didn\'t catch all of that. Could you say the full number again for me?" '
        f"Then call {tool} again with whatever they say, even if it's the same as before."
        f"\n\n{request_state(conv, req)}"
    )
