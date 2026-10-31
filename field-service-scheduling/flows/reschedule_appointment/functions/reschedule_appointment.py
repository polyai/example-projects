from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
import functions.visits as visits
from flows.reschedule_appointment.functions.find_new_time import (
    READBACK_KEY,
    move_fields,
    move_question,
    move_request,
    move_state,
)
from functions.handoff import handoff


@func_description(
    "Move the visit to the window you offered, once the caller has said yes to it. If anything changed since the caller last heard the details, this reads back only the change first."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question this tool's readback asked. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Okay, moving that for you now.", 3), ("Just a moment.", 3)],
)
def reschedule_appointment(conv: Conversation, flow: Flow, caller_confirmed: str):
    if not idnv.is_verified(conv):
        return idnv.require(conv, "reschedule_appointment")
    visit = visits.selected_visit(conv)
    req = move_request(conv)
    if not visit:
        return f"First find out which visit they want to move.\n\n{move_state(conv)}"
    if not req.get("offer"):
        return f"No new window offered yet: call find_new_time.\n\n{move_state(conv)}"

    fields = move_fields(conv, req)
    if not visits.readback_is_current(conv, READBACK_KEY, fields):
        text, mode = visits.readback_text(conv, READBACK_KEY, fields)
        lead = (
            "Read this back" if mode == "full" else "Tell the caller only what changed"
        )
        say = visits.read_back_and_ask(lead, text, "move it")
        return f"NOT MOVED YET. {say}\n\n{move_state(conv)}"
    if str(caller_confirmed).strip().lower() != "true":
        visits.mark_question(conv, READBACK_KEY)
        return (
            f"NOT MOVED YET: {visits.yes_no_question(move_question(conv, req), 'ask')} Once they "
            "clearly say yes, call reschedule_appointment again with caller_confirmed='true'."
            f"\n\n{move_state(conv)}"
        )
    if visits.same_turn_as_question(conv, READBACK_KEY):
        return f"{visits.NOT_DONE_YET}\n\n{move_state(conv)}"

    try:
        api_client.move_appointment(conv, visit["id"], req["offer"])
    except Exception:
        conv.log.error("move_appointment failed", exc_info=True)
        return handoff(
            conv,
            "RESCHEDULE_APPOINTMENT_FAIL",
            "I'm sorry, I couldn't move that visit just now. Let me put you through to a "
            "colleague who can, one moment please.",
            "CUSTOMER_CARE",
        )

    conv.write_metric("MODIFY_APPOINTMENT_FLOW_SUCCESSFUL")
    conv.state.move_request = None
    conv.state.task = ""
    visits.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    when = visits.say_window(req["offer"], visits.today(conv))
    return (
        f"Moved. Tell the caller their visit is now {when}.{visits.reminder_note(conv)} Then ask "
        "if there's anything else."
    )
