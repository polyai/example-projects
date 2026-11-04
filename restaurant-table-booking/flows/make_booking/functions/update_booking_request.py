import functions.new_booking as nb

from _gen import *  # <AUTO GENERATED>
from functions import bookings


def _key(day_iso: str, hhmm: str) -> str:
    return f"{day_iso}T{hhmm}"


def _large_party(conv, req: dict, limit: int) -> str:
    conv.write_metric("LARGE_PARTY_COVERS", req["party_size"])
    req["offer"] = None
    nb.save(conv, req)
    # Nothing is checked or offered: leave the flow so the text or transfer stands alone.
    conv.exit_flow()
    n = bookings.say_party(req["party_size"])
    return (
        f"LARGE PARTY: groups of more than {bookings.say_party(limit)} are booked by the team, so "
        "never offer to book or check availability for it. If the caller has already asked for "
        "the form or a text: say "
        f'"{n.capitalize()}, lovely! For groups of more than {bookings.say_party(limit)}, our team '
        'looks after the booking themselves." and in the same reply call start_send_text with '
        "sms_id='large_party' (with any number they gave) and say what it returns, without "
        "asking again whether to text. Otherwise say: "
        f'"{n.capitalize()}, lovely! For groups of more than {bookings.say_party(limit)}, our team '
        "looks after the booking themselves. I can text you a link to our group booking form. "
        "Would you like me to?\" Yes → call start_send_text with sms_id='large_party'. If they "
        f"ask you to book it anyway: \"I'm afraid I can't for a group of {n}. I can text you the "
        "form, or put you through to the team. Which would you prefer?\" If they'd rather talk to "
        "someone, call handoff with handoff_reason=LARGE_PARTY."
    )


@func_description(
    "Check a table: the day, time and party size. Opening hours, availability and the party size limit are checked here. Call it whenever the caller gives or changes any of them, picks one of the times you offered, or asks for the next free table. The name, number and note go to update_booking_details."
)
@func_parameter(
    "party_size", "How many people, as digits, e.g. '4'. Empty if not said."
)
@func_parameter(
    "date", "The day they want as YYYY-MM-DD (use the date guide). Empty if not said."
)
@func_parameter(
    "time",
    "The time they want, 24-hour HH:MM, e.g. '19:00' for 7pm. With no am or pm, a time means pm unless it's clearly lunch. 'any' if they said any time that day. Empty if not said.",
)
@func_parameter(
    "day_said",
    "The caller's own words for the day, e.g. 'this Friday', 'tonight', 'October 22nd'. Empty if they didn't say a day.",
)
@func_parameter(
    "next_available",
    "'true' only when the caller asks for the next or first free table ('whenever you've got'). Otherwise 'false'.",
)
@func_parameter(
    "phone_number",
    "A corrected contact number the caller gave in this same reply, as they said it (words or digits). Empty otherwise; numbers otherwise go to update_booking_details.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me just check what we've got.", 3), ("One more moment.", 3)],
)
def update_booking_request(
    conv: Conversation,
    flow: Flow,
    party_size: str,
    date: str,
    time: str,
    day_said: str,
    next_available: str,
    phone_number: str,
):
    if conv.state.booked_booking_id:
        return (
            "This table is already booked. If the caller wants to change it, call "
            "start_change_booking; for another table, call start_make_booking."
        )

    req = nb.booking_request(conv)
    before = (req["party_size"], req["date"], req["time"])

    if str(phone_number or "").strip():
        retry = nb.take_phone(conv, req, phone_number, "update_booking_request")
        if retry is not None:
            return retry
    party = bookings.parse_party(party_size)
    if party:
        req["party_size"] = party
    if str(date or "").strip() or str(day_said or "").strip():
        day, problem = bookings.resolve_day(conv, date, day_said)
        if problem:
            nb.save(conv, req)
            return f"{problem} Then call update_booking_request again.\n\n{nb.request_state(conv, req)}"
        if day:
            req["date"] = day.isoformat()
    any_time = bookings.is_any_time(time)
    hhmm = bookings.parse_time(time)
    if hhmm:
        req["time"] = hhmm
    elif any_time:
        req["time"] = "any"

    # Party size limit (settings.max_party_size): larger groups aren't booked here.
    limit = bookings.max_party_size(conv)
    if req["party_size"] > limit:
        return _large_party(conv, req, limit)

    if bookings.is_true(next_available) and not hhmm and not str(date or "").strip():
        if not req["party_size"]:
            nb.save(conv, req)
            return (
                'Ask: "And how many people will it be for?" Then call update_booking_request '
                "again with next_available='true'."
            )
        soonest = bookings.next_free(conv, req["party_size"])
        if soonest is None:
            nb.save(conv, req)
            return (
                f"Nothing is free for {bookings.say_party(req['party_size'])} in the next week. Say "
                "so, and ask if they'd like to be put through to the team.\n\n"
                + nb.request_state(conv, req)
            )
        day, first = soonest
        req["offered"] = [_key(day.isoformat(), first)]
        req["offer"] = None
        nb.save(conv, req)
        return (
            f"Say: \"The first table we've got for {bookings.say_party(req['party_size'])} is "
            f'{bookings.short_when(conv, day.isoformat(), first)}. Would that work for you?" If '
            f"they agree, call update_booking_request with date {day.isoformat()} and time {first}.\n\n"
            + nb.request_state(conv, req)
        )

    missing = nb.missing_details(req)
    if missing:
        nb.save(conv, req)
        return (
            f"{missing[0]} Then call update_booking_request with the answer.\n\n"
            + nb.request_state(conv, req)
        )

    now_asked = (req["party_size"], req["date"], req["time"])
    if req.get("offer") and now_asked == before:
        nb.save(conv, req)
        return nb.after_details(conv, req)

    wanted = "" if req["time"] == "any" else req["time"]
    day = bookings.parse_date(conv, req["date"])
    chosen = bool(wanted) and _key(req["date"], wanted) in req["offered"]
    had_table = bool(req.get("offer"))
    result = bookings.check_table(conv, day, wanted, req["party_size"])
    conv.write_metric("AVAILABILITY_RESULT", result["outcome"])
    if result["outcome"] != "free":
        req["offer"] = None
        dates = (
            [d for d, _ in bookings.nearest_days(conv, day, wanted, req["party_size"])]
            if result["outcome"] == "day_full"
            else []
        )
        offered = [_key(req["date"], t) for t in result.get("times", [])]
        for d in dates:
            offered += [
                _key(d.isoformat(), t)
                for t in bookings.free_times(conv, d, wanted, req["party_size"])
            ]
        before_offered = set(req["offered"])
        req["offered"] = offered
        nb.save(conv, req)
        same = bool(offered) and set(offered) <= before_offered
        if same:
            return (
                "NOT AVAILABLE, and these are the same free times you already gave the caller. "
                "Never offer one they turned down again. If none fits what they asked for, say "
                f"so (\"I'm sorry, we're fully booked after {bookings.say_time(wanted) if wanted else 'then'} "
                f'on {day.strftime("%A")} too.") and ask if another day might work.\n\n'
                + nb.request_state(conv, req)
            )
        return (
            f"NOT AVAILABLE. {result['say']} When they pick a time, call update_booking_request with "
            f"it.\n\n{nb.request_state(conv, req)}"
        )  # fmt: skip

    req["time"] = result["time"]
    req["offer"] = {"date": req["date"], "time": result["time"]}
    req["offered"] = []
    nb.save(conv, req)
    conv.write_metric("TABLE_HELD")
    table = f"a table for {bookings.say_party(req['party_size'])} {bookings.when(conv, req['date'], req['time'])}"
    if chosen:
        lead = (
            f"HELD: {table}. The caller chose this time from the ones you offered, so don't say "
            'it\'s free again: say a short "Great." or "Lovely." and go on. '
        )
    elif had_table and _heard(conv):
        lead = (
            f"FREE: {table}. Say it's free too (\"We've got a table at "
            f'{bookings.say_time(req["time"])} too."), then go on. '
        )
    else:
        free_line = (
            f"Yes, we've got a table for {bookings.say_party(req['party_size'])} at "
            f"{bookings.say_time(req['time'])} {_day_after(conv, req['date'], req['time'])}."
        )
        if not req["name"]:
            # The design's free line stands alone; the caller's reply ("perfect", "okay") is
            # information acknowledged, and the name question comes next.
            return {
                "utterance": free_line,
                "content": 'When the caller replies, ask: "What name should I book it under?" '
                'An "okay" or "perfect" here agrees to nothing: just ask the name.',
            }
        lead = f'FREE: {table}. Say "{free_line}", with no other times, then go on. '
    return nb.after_details(conv, req, lead)


def _heard(conv) -> bool:
    store = conv.state.readbacks if isinstance(conv.state.readbacks, dict) else {}
    return nb.READBACK_KEY in store


def _day_after(conv, day_iso: str, hhmm: str) -> str:
    """'tonight', 'tomorrow', 'on Friday': the day, after the time in the free line."""
    day = bookings.goodbye_day(conv, day_iso)
    return "today" if day == "tonight" and hhmm < "17:00" else day
