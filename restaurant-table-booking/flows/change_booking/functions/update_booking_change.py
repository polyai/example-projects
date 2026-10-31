from functions.handoff import handoff

from _gen import *  # <AUTO GENERATED>
from functions import bookings, idnv


def readback_key(booking_id: str) -> str:
    return f"change:{booking_id}"


def change_fields(conv, values: dict) -> list[tuple[str, str]]:
    fields = [
        ("party", f"for {bookings.say_party(values['party_size'])}"),
        ("when", bookings.say_when(conv, values["date"], values["time"])),
    ]
    if values.get("notes"):
        fields.append(("notes", f"note: {values['notes']}"))
    return fields


def pending_change(conv) -> dict | None:
    change = conv.state.booking_change
    booking = bookings.selected(conv)
    if (
        not isinstance(change, dict)
        or not booking
        or change.get("booking_id") != booking["id"]
    ):
        return None
    return dict(change)


def start_change(conv, booking: dict) -> str:
    """Remember the booking as the caller hears it, so later readbacks give only the change."""
    conv.state.booking_change = {
        "booking_id": booking["id"],
        "party_size": booking["party_size"],
        "date": booking["date"],
        "time": booking["time"],
        "notes": booking.get("notes", ""),
        "offer": None,
        "declined": [],
    }
    bookings.remember_readback(
        conv, readback_key(booking["id"]), change_fields(conv, booking)
    )
    return (
        f"Read the booking back in one natural sentence: {bookings.describe_booking(conv, booking)}. "
        "If the caller has already said what they want to change, call update_booking_change with "
        f"it now; otherwise ask what they'd like to change.\n\n{change_state(conv)}"
    )


def _proposed(change: dict) -> dict:
    offer = change.get("offer") or {}
    return {
        "party_size": change["party_size"],
        "date": offer.get("date", change["date"]),
        "time": offer.get("time", change["time"]),
        "notes": change["notes"],
    }


def change_question(conv, booking: dict, change: dict) -> str:
    """The yes-or-no question for this change, naming the action and only what changes."""
    p = _proposed(change)
    parts = []
    if str(p["party_size"]) != str(booking.get("party_size", "")):
        parts.append(bookings.say_party(p["party_size"]))
    if (p["date"], p["time"]) != (booking.get("date"), booking.get("time")):
        parts.append(bookings.short_when(conv, p["date"], p["time"]))
    if p["notes"] != booking.get("notes", "") and p["notes"]:
        parts.append(f"the note '{p['notes']}'")
    what = " and ".join(parts) or bookings.short_table(
        conv, p["party_size"], p["date"], p["time"]
    )
    return f"Shall I change your booking to {what}"


def is_different(booking: dict, change: dict) -> bool:
    p = _proposed(change)
    return any(
        str(p[k]) != str(booking.get(k, ""))
        for k in ("party_size", "date", "time", "notes")
    )


def change_state(conv) -> str:
    booking = bookings.selected(conv)
    change = pending_change(conv)
    lines = ["Task: change a booking"]
    if booking:
        lines.append(f"Booking now: {bookings.describe_booking(conv, booking)}")
    nxt = "Ask what they'd like to change."
    if booking and change and is_different(booking, change):
        lines.append(f"Proposed: {bookings.describe_booking(conv, _proposed(change))}")
        nxt = (
            "Wait for a clear yes or no to the change, or another change. 'Okay' or 'mm-hm' is "
            "not a yes: ask the yes-or-no question again."
        )
    return bookings.call_state(conv, lines, nxt)


@func_description(
    "Save the change the caller wants to their booking (day, time, party size or a note) and check it: opening hours and availability are checked here, and it gives you the yes-or-no question to ask. Call it whenever they ask for a change or turn down the time you offered."
)
@func_parameter(
    "party_size", "The new number of people, as digits, e.g. '6'. Empty if unchanged."
)
@func_parameter(
    "date", "The new day as YYYY-MM-DD (use the date guide). Empty if unchanged."
)
@func_parameter(
    "time", "The new time, 24-hour HH:MM, e.g. '20:00' for 8pm. Empty if unchanged."
)
@func_parameter("notes", "A note or special request to add. Empty if none.")
@func_parameter(
    "wants_different_time",
    "'true' only when the caller turned down the time you offered without saying what they want instead. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me check that for you.", 3), ("One more moment.", 3)],
)
def update_booking_change(
    conv: Conversation,
    flow: Flow,
    party_size: str,
    date: str,
    time: str,
    notes: str,
    wants_different_time: str,
):
    if not idnv.is_verified(conv):
        return idnv.require(conv, "change_booking")
    booking = bookings.selected(conv)
    if not booking:
        return "First find out which booking they want to change, then call choose_booking."
    change = pending_change(conv)
    if change is None:
        start_change(conv, booking)
        change = pending_change(conv) or {}

    before = (change["party_size"], change["date"], change["time"])
    party = bookings.parse_party(party_size)
    if party:
        change["party_size"] = party
    day = bookings.parse_date(conv, date)
    if day:
        change["date"] = day.isoformat()
    hhmm = bookings.parse_time(time)
    if hhmm:
        change["time"] = hhmm
    if notes.strip() and notes.strip().lower() not in ("na", "none", "no", "nothing"):
        change["notes"] = notes.strip()

    limit = bookings.max_party_size(conv)
    if change["party_size"] > limit:
        conv.state.booking_change = {**change, "offer": None}
        return (
            f"We can't book tables for more than {bookings.say_party(limit)} over the phone. Tell "
            "the caller that, and ask if you can text them the link to our group booking form. "
            "Yes → call start_send_text with sms_id='large_party' and any number they gave (don't transfer). Only if they'd "
            "rather speak to someone, call handoff with handoff_reason=LARGE_PARTY."
        )

    rejected = bookings.is_true(wants_different_time) and bool(change["offer"])
    if rejected:
        change["declined"] = change["declined"] + [change["offer"]["time"]]
        if len(change["declined"]) >= bookings.MAX_REJECTED_OFFERS:
            conv.state.booking_change = change
            return handoff(
                conv,
                "OFFERED_TIME_REJECTED",
                "I'm sorry I couldn't find a time that suits. Let me put you through to the team, "
                "one moment please.",
            )

    note = ""
    moved = before != (change["party_size"], change["date"], change["time"])
    if moved or rejected or not change["offer"]:
        # Every change of party, day or time is re-checked, without counting this booking's own table.
        found, note = bookings.find_time(
            conv,
            bookings.parse_date(conv, change["date"]),
            change["time"],
            change["party_size"],
            declined=change["declined"],
            ignore_booking_id=booking["id"],
        )
        if found is None:
            change["offer"] = None
            change["party_size"], change["date"], change["time"] = before
            conv.state.booking_change = change
            return f"{note} The booking is unchanged so far.\n\n{change_state(conv)}"
        change["offer"] = {"date": change["date"], "time": found}
    conv.state.booking_change = change

    if not is_different(booking, change):
        return (
            "That's the same as the booking already. Say so and ask what they'd like to change."
            f"\n\n{change_state(conv)}"
        )
    # The question names exactly what changes; record that the caller has heard it.
    key = readback_key(booking["id"])
    bookings.readback_text(conv, key, change_fields(conv, _proposed(change)))
    bookings.mark_asked(conv, key)
    ask = bookings.ask_yes_no(change_question(conv, booking, change))
    return f"{note} {ask}".strip() + f"\n\n{change_state(conv)}"
