from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
import functions.visits as visits
from flows.schedule_appointment.functions.update_visit_request import (
    READBACK_KEY,
    booking_fields,
    booking_question,
    missing_details,
    request_state,
    visit_request,
)
from functions.handoff import handoff


@func_description(
    "Book the arrival window you offered, once the caller has said yes to it. If anything changed since the caller last heard the details, this reads back only the change first."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question this tool's readback asked. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Okay, booking that in for you now.", 3), ("Just a moment.", 3)],
)
def make_new_appointment(conv: Conversation, flow: Flow, caller_confirmed: str):
    if not idnv.is_verified(conv):
        return idnv.require(conv, "schedule_appointment")
    if conv.state.booked_appointment_id:
        return "This visit is already booked; don't book it again. Ask if there's anything else."

    req = visit_request(conv)
    missing = missing_details(req)
    if missing:
        return f"Not ready to book: ask for {missing[0]}.\n\n{request_state(conv)}"
    if not req.get("offer"):
        return f"No window has been offered yet: call find_visit_time.\n\n{request_state(conv)}"

    fields = booking_fields(conv, req)
    if not visits.readback_is_current(conv, READBACK_KEY, fields):
        text, mode = visits.readback_text(conv, READBACK_KEY, fields)
        lead = (
            "Read this back" if mode == "full" else "Tell the caller only what changed"
        )
        say = visits.read_back_and_ask(lead, text, "book it")
        return f"NOT BOOKED YET. {say}\n\n{request_state(conv)}"
    if str(caller_confirmed).strip().lower() != "true":
        visits.mark_question(conv, READBACK_KEY)
        return (
            f"NOT BOOKED YET: {visits.yes_no_question(booking_question(conv, req), 'ask')} Once they clearly say yes, call make_new_appointment "
            f"again with caller_confirmed='true'.\n\n{request_state(conv)}"
        )
    if visits.same_turn_as_question(conv, READBACK_KEY):
        return f"{visits.NOT_DONE_YET}\n\n{request_state(conv)}"

    customer = idnv.customer(conv)
    if not customer:
        return idnv.require(conv, "schedule_appointment")
    try:
        appt = api_client.create_appointment(
            conv,
            customer["id"],
            req["offer"],
            {
                "service_type": req["service_type"],
                "issue": req["issue"],
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
            "I'm sorry, I couldn't complete that booking just now. Let me put you through to a "
            "colleague who can, one moment please.",
            "CUSTOMER_CARE",
        )

    conv.state.booked_appointment_id = appt["id"]
    conv.state.task = ""
    conv.write_metric("MAKE_APPOINTMENT_FLOW_SUCCESSFUL")
    visits.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    when = visits.say_window(appt, visits.today(conv))
    prep = (
        f" Then give the visit prep: {visits.prep_note(conv)} {visits.INDOOR_PREP_HINT}"
        if req["indoor"]
        else ""
    )
    return (
        f"Booked. Tell the caller they're all set for {when}.{prep}{visits.reminder_note(conv)} "
        "Don't repeat the other details. Then ask if there's anything else."
    )
