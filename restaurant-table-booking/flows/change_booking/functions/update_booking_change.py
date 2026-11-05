import functions.existing_booking as existing
from _gen import *  # <AUTO GENERATED>
from functions import bookings


def _key(day_iso: str, hhmm: str) -> str:
    return f"{day_iso}T{hhmm}"


@func_description(
    "Check the change the caller wants to their booking: the day, time, party size or a note. Opening hours and availability are checked here, and it gives you the question to ask. Call it whenever they ask for a change or pick one of the times you offered."
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
@func_parameter(
    "notes", "A note to add, in a few of the caller's words. Empty if none."
)
@func_parameter(
    "day_said",
    "The caller's own words for the new day, e.g. 'Saturday', 'next Friday'. Empty if they didn't say a day.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me just check what we've got.", 3), ("One more moment.", 3)],
)
def update_booking_change(
    conv: Conversation,
    flow: Flow,
    party_size: str,
    date: str,
    time: str,
    notes: str,
    day_said: str,
):
    gate = bookings.require(conv, "change_booking")
    if gate:
        return gate
    booking = bookings.selected(conv)
    if not booking:
        return "First find out which booking they want to change, then call choose_booking."
    change = existing.pending_change(conv)
    if change is None:
        existing.start_change(conv, booking)
        change = existing.pending_change(conv) or {}

    current = existing.proposed(change)
    wanted = {
        "party_size": current["party_size"],
        "date": current["date"],
        "time": current["time"],
    }
    party = bookings.parse_party(party_size)
    if party:
        wanted["party_size"] = party
    if str(date or "").strip() or str(day_said or "").strip():
        day, problem = bookings.resolve_day(conv, date, day_said)
        if problem:
            return f"{problem} Then call update_booking_change again.\n\n{existing.change_state(conv)}"
        if day:
            wanted["date"] = day.isoformat()
    hhmm = bookings.parse_time(time)
    if hhmm:
        wanted["time"] = hhmm
    note = str(notes or "").strip()
    if note and note.lower() not in ("na", "none", "no", "nothing"):
        change["notes"] = note

    limit = bookings.max_party_size(conv)
    if wanted["party_size"] > limit:
        conv.state.booking_change = {**change, "offer": None}
        conv.write_metric("LARGE_PARTY_COVERS", wanted["party_size"])
        return (
            f"LARGE PARTY: groups of more than {bookings.say_party(limit)} are booked by the team, "
            "so the booking stays as it is. Say so, and offer to text a link to our group booking "
            "form (yes → call start_send_text with sms_id='large_party'), or to put them through "
            "to the team (handoff with handoff_reason=LARGE_PARTY)."
        )

    chosen = _key(wanted["date"], wanted["time"]) in change.get("offered", [])
    day = bookings.parse_date(conv, wanted["date"])
    moved = (wanted["party_size"], wanted["date"], wanted["time"]) != (
        booking["party_size"],
        booking["date"],
        booking["time"],
    )
    lead = ""
    if moved:
        # Every change of party, day or time is re-checked, without this booking's own table.
        result = bookings.check_table(
            conv, day, wanted["time"], wanted["party_size"], booking["id"]
        )
        if result["outcome"] != "free":
            change["offer"] = None
            change["offered"] = [
                _key(wanted["date"], t) for t in result.get("times", [])
            ]
            for d, times in (
                bookings.nearest_days(
                    conv, day, wanted["time"], wanted["party_size"], booking["id"]
                )
                if result["outcome"] == "day_full"
                else []
            ):
                change["offered"] += [_key(d.isoformat(), t) for t in times]
            conv.state.booking_change = change
            return (
                f"NOT AVAILABLE. {result['say']} The booking stays as it is until they agree a "
                "time. When they pick one, call update_booking_change with it.\n\n"
                + existing.change_state(conv)
            )
        wanted["time"] = result["time"]
        if not chosen:
            if wanted["party_size"] != booking["party_size"] and (
                wanted["date"],
                wanted["time"],
            ) == (booking["date"], booking["time"]):
                lead = f"That's fine, we've got room for {bookings.say_party(wanted['party_size'])} at {bookings.say_time(wanted['time'])}. "
            elif wanted["date"] == booking["date"]:
                lead = f"We've got a table at {bookings.say_time(wanted['time'])} that night. "
            else:
                lead = f"We've got a table at {bookings.say_time(wanted['time'])} on {day.strftime('%A')}. "
    change.update(
        party_size=wanted["party_size"], date=wanted["date"], time=wanted["time"]
    )
    change["offer"] = {"date": wanted["date"], "time": wanted["time"]}
    change["offered"] = []
    conv.state.booking_change = change

    if not existing.is_different(booking, change):
        change["offer"] = None
        conv.state.booking_change = change
        return (
            "That's the same as the booking already. Say so and ask what they'd like to change."
            f"\n\n{existing.change_state(conv)}"
        )
    key = existing.change_key(booking["id"])
    bookings.readback_changes(
        conv, key, existing.change_fields(conv, existing.proposed(change))
    )
    bookings.mark_asked(conv, key)
    question = existing.change_question(conv, booking, change)
    return (
        f'NOT CHANGED YET. Say: "{lead}{question}" A yes, or an acknowledgement to that question '
        '("okay", "sure", "go on"), is a yes: call modify_booking with caller_confirmed=\'true\'.'
        f"\n\n{existing.change_state(conv)}"
    )
