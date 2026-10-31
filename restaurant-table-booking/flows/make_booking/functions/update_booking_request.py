from functions.handoff import handoff

from _gen import *  # <AUTO GENERATED>
from functions import bookings, idnv

READBACK_KEY = "new_booking"


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
            "notes": "",
            "offer": None,
            "declined": [],
            "phone_unclear": 0,
        }
    return dict(req)


def missing_details(req: dict) -> list[str]:
    missing = []
    if not req["party_size"]:
        missing.append("how many people")
    if not req["date"] and not req["time"]:
        missing.append("what day and time they'd like")
    elif not req["date"]:
        missing.append("what day they'd like")
    elif not req["time"]:
        missing.append("what time they'd like")
    return missing


def contact_text(req: dict) -> str:
    if not req["phone"]:
        return ""
    if req["phone_from_caller_id"]:
        return "on the number you're on now"
    return f"your number {idnv.spell_phone(req['phone'])}"


def booking_fields(conv, req: dict) -> list[tuple[str, str]]:
    offer = req.get("offer") or {}
    fields = [
        (
            "party",
            f"a table for {bookings.say_party(req['party_size'])}"
            if req["party_size"]
            else "",
        ),
        (
            "when",
            bookings.say_when(conv, offer["date"], offer["time"]) if offer else "",
        ),
        ("name", f"under {req['name']}" if req["name"] else ""),
        ("contact", contact_text(req)),
    ]
    if req["notes"]:
        fields.append(("notes", f"note: {req['notes']}"))
    return fields


def next_step(conv, req: dict) -> str:
    missing = missing_details(req)
    if missing:
        return f"Ask {missing[0]}."
    if not req.get("offer"):
        return "Call update_booking_request to find a time to offer."
    if not req["name"]:
        return "Ask what name the booking should be under, then call update_booking_details with it."
    if not req["phone"]:
        return "Ask for the best phone number to reach them, then call update_booking_details with it."
    return (
        "Wait for a clear yes or no to booking it, or a change. 'Okay' or 'mm-hm' is not a yes: "
        "ask the yes-or-no question again."
    )


def request_state(conv) -> str:
    req = booking_request(conv)
    offer = req.get("offer")
    lines = [
        "Task: book a table",
        "Party: "
        + (bookings.say_party(req["party_size"]) if req["party_size"] else "not given"),
        "Asked for: "
        + (" ".join(x for x in (req["date"], req["time"]) if x) or "nothing yet"),
        "Offered: "
        + (
            bookings.say_when(conv, offer["date"], offer["time"])
            if offer
            else "nothing yet"
        ),
        "Name: " + (req["name"] or "not given"),
        "Contact number: "
        + (contact_text(req).removeprefix("contact number").strip(": ") or "not given"),
    ]
    if req["notes"]:
        lines.append(f"Notes: {req['notes']}")
    return bookings.call_state(conv, lines, next_step(conv, req))


def save(conv, req: dict) -> None:
    conv.state.booking_request = req


def offer_or_readback(conv, req: dict, note: str = "") -> str:
    """Once a time is offered: ask for the name or number still missing, or give
    the yes-or-no question to book it. Shared by update_booking_request and update_booking_details,
    whichever completes the booking's details."""
    calling = idnv.normalize_phone(conv.state.caller_phone)
    offer_text = (
        f"a table for {bookings.say_party(req['party_size'])} "
        f"{bookings.say_when(conv, req['offer']['date'], req['offer']['time'])}"
    )
    if not req["name"]:
        return (
            f"Tell the caller {offer_text} is free, in one short sentence. {note} Then ask what "
            "name the booking should be under, and call update_booking_details with it.\n\n"
            f"{request_state(conv)}"
        )
    if not req["phone"]:
        if idnv.is_valid_phone(calling):
            req["phone"], req["phone_from_caller_id"] = calling, True
            save(conv, req)
        else:
            return (
                f"Tell the caller {offer_text} is free, in one short sentence. {note} Then ask for "
                "the best phone number to reach them, and call update_booking_details with it."
                f"\n\n{request_state(conv)}"
            )

    confirm = confirm_booking(conv, req)
    return f"{note} {confirm}".strip() + f"\n\n{request_state(conv)}"


# The details the booking question names. A note isn't in it; a change to the note
# after the question is said before it is asked again. A number the caller gave is
# in it, since this is their only chance to hear it and correct a misheard digit;
# the number they're calling from isn't read out.
QUESTION_FIELDS = ("party", "when", "name", "contact")


def book_question(conv, req: dict) -> str:
    """The yes-or-no question for this booking: the action, the table, the name and
    any number the caller gave."""
    offer = req["offer"]
    question = f"Shall I book {bookings.short_table(conv, req['party_size'], offer['date'], offer['time'])}"
    if req["name"]:
        question += f" under {req['name']}"
    if req["phone"] and not req["phone_from_caller_id"]:
        question += f", on {idnv.spell_phone(req['phone'])}"
    return question


def confirm_booking(conv, req: dict) -> str:
    """Record what the caller is about to hear and return the yes-or-no question,
    led by any changed detail the question doesn't name."""
    changed, mode = bookings.readback_changes(
        conv, READBACK_KEY, booking_fields(conv, req)
    )
    bookings.mark_asked(conv, READBACK_KEY)
    extra = (
        [v for k, v in changed.items() if k not in QUESTION_FIELDS]
        if mode == "changes"
        else []
    )
    return bookings.ask_yes_no(book_question(conv, req), "; ".join(extra))


@func_description(
    "Check the table the caller wants: opening hours, availability and the party size limit are checked here, and it offers one time. Call it whenever they give or change the party size, day or time, or turn down the time you offered. The name, number and any note go to update_booking_details."
)
@func_parameter(
    "party_size", "How many people, as digits, e.g. '4'. Empty if not said."
)
@func_parameter(
    "date", "The day they want as YYYY-MM-DD (use the date guide). Empty if not said."
)
@func_parameter(
    "time",
    "The time they want, 24-hour HH:MM, e.g. '19:00' for 7pm. With no am or pm, assume pm for dinner hours. Empty if not said.",
)
@func_parameter(
    "wants_different_time",
    "'true' only when the caller turned down the time you offered without saying what they want instead. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me just check what we have.", 3), ("One more moment.", 3)],
)
def update_booking_request(
    conv: Conversation,
    flow: Flow,
    party_size: str,
    date: str,
    time: str,
    wants_different_time: str,
):
    if conv.state.booked_booking_id:
        return (
            "This table is already booked. If the caller wants to change it, call "
            "start_change_booking; for another table, call start_make_booking."
        )

    req = booking_request(conv)
    before = (req["party_size"], req["date"], req["time"])

    party = bookings.parse_party(party_size)
    if party:
        req["party_size"] = party
    day = bookings.parse_date(conv, date)
    if day:
        req["date"] = day.isoformat()
    hhmm = bookings.parse_time(time)
    if hhmm:
        req["time"] = hhmm

    # Party size limit (settings.max_party_size): larger groups aren't booked here.
    limit = bookings.max_party_size(conv)
    if req["party_size"] > limit:
        conv.write_metric("LARGE_PARTY_COVERS", req["party_size"])
        req["offer"] = None
        save(conv, req)
        # Nothing more to book here: leave the flow so the text or transfer stands alone.
        conv.exit_flow()
        return (
            f"We can't book tables for more than {bookings.say_party(limit)} over the phone. Tell "
            "the caller that, and ask if you can text them the link to our group booking form. "
            "Yes → call start_send_text with sms_id='large_party' and any number they gave (don't "
            "transfer). Only if they'd rather speak to someone, call handoff with "
            "handoff_reason=LARGE_PARTY."
        )

    rejected = bookings.is_true(wants_different_time) and bool(req["offer"])
    if rejected:
        req["declined"] = req["declined"] + [req["offer"]["time"]]
        conv.write_metric("OFFERED_TIME_REJECTED")
        if len(req["declined"]) >= bookings.MAX_REJECTED_OFFERS:
            save(conv, req)
            return handoff(
                conv,
                "OFFERED_TIME_REJECTED",
                "I'm sorry I couldn't find a time that suits. Let me put you through to the team, "
                "one moment please.",
            )

    missing = missing_details(req)
    if missing:
        save(conv, req)
        return (
            f"Saved. Ask {missing[0]}, then call update_booking_request with the answer."
            f"\n\n{request_state(conv)}"
        )

    note = ""
    changed = before != (req["party_size"], req["date"], req["time"])
    if changed and not rejected:
        req["declined"] = [] if before[1] != req["date"] else req["declined"]
    if changed or rejected or not req["offer"]:
        # Any change to the party, day or time re-checks availability before anything is offered.
        day = bookings.parse_date(conv, req["date"])
        found, note = bookings.find_time(
            conv, day, req["time"], req["party_size"], declined=req["declined"]
        )
        if found is None:
            req["offer"] = None
            save(conv, req)
            return f"{note}\n\n{request_state(conv)}"
        req["offer"] = {"date": req["date"], "time": found}
    save(conv, req)
    conv.write_metric("TIME_OFFERED")
    return offer_or_readback(conv, req, note)
