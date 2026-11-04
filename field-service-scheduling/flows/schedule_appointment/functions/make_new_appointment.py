from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
import functions.visits as visits
from flows.schedule_appointment.functions.update_visit_request import (
    LOOKUP_KEY,
    READBACK_KEY,
    booking_fields,
    booking_readback,
    check_open,
    first_readback,
    missing_detail,
    request_state,
    visit_request,
)
from functions.handoff import handoff
from functions.utils import variant_attr


def done_line(conv, appt: dict, indoor: bool) -> str:
    """The booked line: what was booked, the someone-home sentence for an indoor visit, then an
    offer of more help."""
    now = visits.today(conv)
    line = (
        f"Lovely, you're all booked for {visits.short_day(appt['date'], now)}, with the "
        f"technician arriving {visits.between(appt)}."
    )
    if indoor:
        line += f" {visits.home_line(conv)}"
    return f"{line} Is there anything else I can help with?"


@func_description(
    "Book the arrival window the caller chose. Call it first with caller_confirmed='false': it books nothing and returns the readback to say. Call it again with 'true' once the caller agrees to that readback question."
)
@func_parameter(
    "visit_date",
    "The date of the window they chose, as YYYY-MM-DD, from find_visit_time.",
)
@func_parameter(
    "window_start",
    "The start of the window they chose, as HH:MM 24-hour, e.g. '09:00' or '13:00'.",
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply agreed to the readback question this tool returned. 'Okay', 'sure', 'sounds good' or 'go on' to that question is agreement; an answer to something else, a question back or real hesitation is not. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Booking that in for you now.", 3), ("Nearly there.", 3)],
)
def make_new_appointment(
    conv: Conversation,
    flow: Flow,
    visit_date: str,
    window_start: str,
    caller_confirmed: str,
):
    refusal = check_open(conv)
    if refusal:
        return refusal
    req = visit_request(conv)
    missing = missing_detail(req)
    if missing:
        return f'NOT BOOKED: first ask: "{missing}"\n\n{request_state(conv)}'
    window = visits.chosen_window(conv, LOOKUP_KEY, visit_date, window_start)
    if not window:
        return (
            f"NOT BOOKED: {visit_date} {window_start} isn't one of the windows you looked up. "
            "Call find_visit_time with the day they want, then offer only what it returns."
            f"\n\n{request_state(conv)}"
        )

    fields = booking_fields(conv, req, window)
    question = booking_readback(conv, req, window)
    if not visits.readback_is_current(conv, READBACK_KEY, fields):
        heard_before = bool(visits.heard(conv, READBACK_KEY))
        changed, _ = visits.readback_text(conv, READBACK_KEY, fields)
        if heard_before:
            say = booking_readback(conv, req, window, only=changed)
            lead = "Say only what changed"
        else:
            say = first_readback(conv, req, window)
            lead = "Say this"
        pricing = variant_attr(conv, "pricing_info")
        cost = (
            f" If they ask what it costs, answer only the relevant part of this, in one sentence, "
            f'then ask again whether to book it: "{pricing}"'
            if pricing
            else ""
        )
        return (
            f'NOT BOOKED YET. {lead}, word for word, then wait for the answer: "{say}"{cost}'
            f"\n\n{request_state(conv)}"
        )
    if str(caller_confirmed).strip().lower() != "true":
        return visits.ask_again(conv, READBACK_KEY, question)
    if visits.same_turn_as_question(conv, READBACK_KEY):
        return visits.ask_again(conv, READBACK_KEY, question)

    customer = idnv.customer(conv)
    if not customer:
        return idnv.require(conv, "schedule_appointment")
    if not api_client.window_is_open(conv, window):
        visits.forget_readback(conv, READBACK_KEY)
        found = visits.lookup(conv, LOOKUP_KEY, window["date"], "")
        others = visits.availability_text(conv, found, "make_new_appointment")
        return (
            "NOT BOOKED: that window was taken just now. Say: \"I'm sorry, that window's just "
            'been taken. I could do …" and offer the two windows below that best fit.\n'
            f"{others}"
        )
    try:
        appt = api_client.create_appointment(
            conv,
            customer["id"],
            window,
            {
                "service_type": req["service_type"],
                "issue": visits.heard(conv, READBACK_KEY).get("problem", req["issue"]),
                "location": req["location"],
                "indoor": req["indoor"],
                "notes": req["notes"],
            },
        )
    except Exception:
        conv.log.error("create_appointment failed", exc_info=True)
        return handoff(
            conv,
            "SCHEDULE_APPOINTMENT_FAIL",
            "I'm sorry, I couldn't book that just now. Let me put you through to the team, who "
            "can. One moment, please.",
            "CUSTOMER_CARE",
        )

    conv.state.booked_appointment_id = appt["id"]
    conv.state.see_you_date = appt["date"]
    conv.state.task = ""
    conv.write_metric("MAKE_APPOINTMENT_FLOW_SUCCESSFUL")
    visits.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    return {"utterance": done_line(conv, appt, bool(req["indoor"]))}
