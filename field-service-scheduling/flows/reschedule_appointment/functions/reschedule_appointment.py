from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
import functions.visits as visits
from flows.reschedule_appointment.functions.find_new_time import (
    LOOKUP_KEY,
    READBACK_KEY,
    move_fields,
    move_question,
    move_state,
)
from functions.handoff import handoff


def done_line(conv, window: dict) -> str:
    """Where the visit moved to, then an offer of more help. No reminder sentence."""
    day = visits.short_day(window["date"], visits.today(conv))
    return (
        f"I've moved your visit to {day}, with the technician arriving {visits.between(window)}. "
        "Is there anything else I can help with?"
    )


@func_description(
    "Move the visit to the window the caller chose. Call it first with caller_confirmed='false': it moves nothing and returns the question to ask. Call it again with 'true' once the caller agrees to that question."
)
@func_parameter(
    "visit_date",
    "The date of the window they chose, as YYYY-MM-DD, from find_new_time.",
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
    delay_responses=[("Moving that for you now.", 3), ("Nearly there.", 3)],
)
def reschedule_appointment(
    conv: Conversation,
    flow: Flow,
    visit_date: str,
    window_start: str,
    caller_confirmed: str,
):
    if not idnv.is_verified(conv):
        return idnv.require(conv, "reschedule_appointment")
    visit = visits.selected_visit(conv)
    if not visit:
        return f"First find out which visit they want to move.\n\n{move_state(conv)}"
    window = visits.chosen_window(conv, LOOKUP_KEY, visit_date, window_start)
    if not window:
        return (
            f"NOT MOVED: {visit_date} {window_start} isn't one of the windows you looked up. Call "
            f"find_new_time with the day they want, then offer only what it returns.\n\n{move_state(conv)}"
        )
    if visits.window_key(window) == visits.window_key(visit):
        return (
            "NOT MOVED: that's when the visit already is. Say so, and ask what day would work "
            f"better for them.\n\n{move_state(conv)}"
        )

    fields = move_fields(conv, window)
    question = move_question(conv, window)
    if not visits.readback_is_current(conv, READBACK_KEY, fields):
        visits.readback_text(conv, READBACK_KEY, fields)
        lead = visits.lead_line(conv, LOOKUP_KEY, window, task="move")
        if lead.startswith("The earliest"):
            say = f"{lead} Shall I move your visit to then?"
        else:
            say = f"{lead} {question}".strip()
        say = visits.thanks(conv) + say
        return (
            f'NOT MOVED YET. Say this, word for word, then wait for the answer: "{say}"\n\n'
            + move_state(conv)
        )
    if str(caller_confirmed).strip().lower() != "true":
        return visits.ask_again(conv, READBACK_KEY, question)
    if visits.same_turn_as_question(conv, READBACK_KEY):
        return visits.ask_again(conv, READBACK_KEY, question)
    if not api_client.window_is_open(conv, window):
        visits.forget_readback(conv, READBACK_KEY)
        found = visits.lookup(conv, LOOKUP_KEY, window["date"], "")
        others = visits.availability_text(
            conv, found, "reschedule_appointment", task="move"
        )
        return (
            "NOT MOVED: that window was taken just now. Say: \"I'm sorry, that window's just "
            'been taken. I could do …" and offer the two windows below that best fit.\n'
            f"{others}"
        )

    try:
        api_client.move_appointment(conv, visit["id"], window)
    except Exception:
        conv.log.error("move_appointment failed", exc_info=True)
        return handoff(
            conv,
            "RESCHEDULE_APPOINTMENT_FAIL",
            "I'm sorry, I couldn't move that visit just now. Let me put you through to the team, "
            "who can. One moment, please.",
            "CUSTOMER_CARE",
        )

    conv.write_metric("MODIFY_APPOINTMENT_FLOW_SUCCESSFUL")
    conv.state.see_you_date = window["date"]
    conv.state.task = ""
    visits.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    return {"utterance": done_line(conv, window)}
