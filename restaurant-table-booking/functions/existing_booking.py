"""Check, change and cancel an existing booking: what to read back and ask, shared by
the entry steps, choose_booking and the flow tools (which import only from functions/).
"""

from datetime import date

from _gen import *  # <AUTO GENERATED>
from functions import bookings

CANCEL_KEY = "cancel"
CANCEL_QUESTION = "Shall I cancel that for you?"


@func_description("[UTIL] Existing booking helpers, not callable directly")
def existing_booking(conv: Conversation):
    return "Existing booking helpers module."


# --- Check ------------------------------------------------------------------


def check_readback(conv, booking: dict) -> str:
    conv.write_metric("CHECK_BOOKING_FLOW_SUCCESSFUL")
    day = bookings.day_name(conv, booking["date"])
    full_day = date.fromisoformat(booking["date"])
    if day in ("today", "tomorrow"):
        day = f"{'tonight' if day == 'today' and booking['time'] >= '17:00' else day}, {full_day.strftime('%A')} the {bookings._ordinal(full_day.day)},"
    else:
        day = f"on {day}"
    note = f", with a note: {booking['notes']}" if booking.get("notes") else ""
    line = (
        f"You've got a table for {bookings.say_party(booking['party_size'])} {day} at "
        f"{bookings.say_time(booking['time'])}, under {booking['first_name']} "
        f"{booking['last_name']}{note}."
    ).replace(" ,", ",")
    return (
        f'Read the booking back in one sentence, adding nothing: "{line}" Then ask: "Is there '
        "anything you'd like to change?\"\n\n"
        + bookings.call_state(
            conv,
            [
                "Task: check a booking",
                f"Booking: {bookings.describe_booking(conv, booking, True)}",
            ],
            "Answer any question about it. To change it call start_change_booking; to cancel it "
            "call start_cancel_booking; for another table call start_make_booking. A text "
            "confirmation can't be sent: read the booking out instead.",
        )
    )


# --- Cancel -----------------------------------------------------------------


def cancel_fields(conv, booking) -> list[tuple[str, str]]:
    return [("booking", bookings.describe_booking(conv, booking) if booking else "")]


def cancel_sentence(conv, booking: dict) -> str:
    """'You've got a table for four tomorrow at 7. Shall I cancel that for you?'"""
    table = bookings.table_for(
        conv, booking["party_size"], booking["date"], booking["time"]
    )
    return f"You've got {table}. {CANCEL_QUESTION}"


def cancel_readback(conv) -> str:
    booking = bookings.selected(conv)
    bookings.readback_changes(conv, CANCEL_KEY, cancel_fields(conv, booking))
    bookings.mark_asked(conv, CANCEL_KEY)
    return (
        f'Say: "{cancel_sentence(conv, booking)}" A yes, or an acknowledgement to that question '
        '("okay", "sure", "go on"), is a yes: call cancel_booking with caller_confirmed=\'true\' '
        "and their reason if they gave one. Never ask for a reason. Real hesitation: answer or "
        "wait, then ask again. If they'd rather move it, call start_change_booking. If they keep "
        'it, say "No problem, your booking\'s still in place."\n\n'
        + bookings.call_state(
            conv,
            [
                "Task: cancel a booking",
                f"Booking: {bookings.describe_booking(conv, booking)}",
            ],
            f'Wait for the answer to "{CANCEL_QUESTION}"',
        )
    )


# --- Change -----------------------------------------------------------------


def change_key(booking_id: str) -> str:
    return f"change:{booking_id}"


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


def proposed(change: dict) -> dict:
    offer = change.get("offer") or {}
    return {
        "party_size": change["party_size"],
        "date": offer.get("date", change["date"]),
        "time": offer.get("time", change["time"]),
        "notes": change["notes"],
    }


def change_fields(conv, values: dict) -> list[tuple[str, str]]:
    return [
        ("party", bookings.say_people(values["party_size"])),
        ("when", bookings.short_when(conv, values["date"], values["time"])),
        ("notes", values.get("notes") or ""),
    ]


def start_change(conv, booking: dict) -> str:
    """Remember the booking as the caller hears it, so the question names only the change."""
    conv.state.booking_change = {
        "booking_id": booking["id"],
        "party_size": booking["party_size"],
        "date": booking["date"],
        "time": booking["time"],
        "notes": booking.get("notes", ""),
        "offer": None,
        "offered": [],
    }
    bookings.remember_readback(
        conv, change_key(booking["id"]), change_fields(conv, booking)
    )
    table = bookings.table_for(
        conv, booking["party_size"], booking["date"], booking["time"]
    )
    return (
        f"If the caller hasn't heard the booking yet, say it in a few words (\"You're booked for "
        f'{table.removeprefix("a table for ")}."). If they have already said what they want to '
        'change, call update_booking_change with it now; otherwise ask: "What would you like to '
        f'change?"\n\n{change_state(conv)}'
    )


def change_question(conv, booking: dict, change: dict) -> str:
    """'Shall I move your booking to 7?', 'Shall I update your booking to six people?',
    'Shall I add that note to your booking?': only what changes."""
    p = proposed(change)
    moved = (p["date"], p["time"]) != (booking["date"], booking["time"])
    bigger = int(p["party_size"]) != int(booking["party_size"])
    if moved:
        same_day = p["date"] == booking["date"]
        to = (
            bookings.say_time(p["time"])
            if same_day
            else bookings.short_when(conv, p["date"], p["time"])
        )
        if bigger:
            return f"Shall I move your booking to {to}, for {bookings.say_people(p['party_size'])}?"
        return f"Shall I move your booking to {to}?"
    if bigger:
        return f"Shall I update your booking to {bookings.say_people(p['party_size'])}?"
    return "Shall I add that note to your booking?"


def change_done(conv, booking: dict, before: dict) -> str:
    """The done line: what changed, then an offer of more help."""
    moved = (booking["date"], booking["time"]) != (before["date"], before["time"])
    bigger = int(booking["party_size"]) != int(before["party_size"])
    when = f"{bookings.say_time(booking['time'])} on {date.fromisoformat(booking['date']).strftime('%A')}"
    if moved and bigger:
        what = f"I've moved your booking to {when}, for {bookings.say_people(booking['party_size'])}."
    elif moved:
        what = f"I've moved your booking to {when}."
    elif bigger:
        what = f"I've updated your booking to be for {bookings.say_people(booking['party_size'])}."
    else:
        what = "I've added that note to your booking."
    return f"{what} Is there anything else I can help with?"


def is_different(booking: dict, change: dict) -> bool:
    p = proposed(change)
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
    nxt = 'Ask: "What would you like to change?"'
    if booking and change and change.get("offer") and is_different(booking, change):
        lines.append(f"Proposed: {bookings.describe_booking(conv, proposed(change))}")
        nxt = (
            f'Wait for the answer to "{change_question(conv, booking, change)}" A yes, or an '
            "acknowledgement to it, is a yes: call modify_booking with caller_confirmed='true'."
        )
    return bookings.call_state(conv, lines, nxt)
