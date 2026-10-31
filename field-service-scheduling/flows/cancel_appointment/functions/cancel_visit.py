from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
import functions.visits as visits
from functions.handoff import handoff

READBACK_KEY = "cancel"


def _fields(conv, visit) -> list[tuple[str, str]]:
    """The visit as the caller says yes to cancelling it: its kind and its window."""
    if not visit:
        return [("visit", "")]
    kind = visit.get("service_type") or "service"
    return [("visit", f"your {kind} visit on {visits.say_slot(visit)}")]


def cancel_readback(conv) -> str:
    """The cancellation readback: the whole visit, every time, and the question it needs a clear
    yes to. The entry step, choose_visit and cancel_visit itself all return this, so nothing is
    cancelled that the caller hasn't heard asked."""
    visit = visits.selected_visit(conv)
    fields = _fields(conv, visit)
    visits.readback_text(
        conv, READBACK_KEY, fields
    )  # record what the caller is about to hear
    visits.mark_question(conv, READBACK_KEY)  # asked again every time
    text = fields[0][1]
    say = visits.read_back_and_ask("read the visit back", text, "cancel it")
    return (
        f"NOT CANCELLED YET: {say} Once they clearly say yes, call cancel_visit with "
        "caller_confirmed='true'.\n\n"
        + visits.call_state(
            conv,
            ["Task: cancel a visit", f"Visit: {text}"],
            "Wait for the caller's yes or no to cancelling it.",
        )
    )


def cancellation_enabled(conv) -> bool:
    settings = (conv.real_time_config or {}).get("settings", {})
    return bool(settings.get("cancel_appointment_flow_enabled", True))


@func_description(
    "Cancel the visit you read back, once the caller has said yes to cancelling it."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question this tool's readback asked. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
)
@func_parameter(
    "reason", "Why they're cancelling, if they said. Empty string otherwise."
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Okay, cancelling that now.", 3), ("Just a moment.", 3)],
)
def cancel_visit(conv: Conversation, flow: Flow, caller_confirmed: str, reason: str):
    if not idnv.is_verified(conv):
        return idnv.require(conv, "cancel_appointment")
    visit = visits.selected_visit(conv)
    if not visit:
        return (
            "NOT CANCELLED: first find out which visit they want to cancel, then call "
            "choose_visit with its date."
        )
    if not visits.readback_is_current(conv, READBACK_KEY, _fields(conv, visit)):
        return cancel_readback(conv)
    if str(caller_confirmed).strip().lower() != "true":
        return cancel_readback(conv)
    if visits.same_turn_as_question(conv, READBACK_KEY):
        return visits.NOT_DONE_YET
    if not cancellation_enabled(conv):
        return handoff(
            conv,
            "CANCEL_APPOINTMENT",
            "For cancellations I'll need to put you through to a colleague. One moment please.",
            "CUSTOMER_CARE",
        )

    try:
        api_client.cancel_appointment(conv, visit["id"], (reason or "").strip())
    except Exception:
        conv.log.error("cancel_appointment failed", exc_info=True)
        return handoff(
            conv,
            "CANCEL_APPOINTMENT_FAIL",
            "I'm sorry, I couldn't cancel that just now. Let me put you through to a colleague "
            "who can, one moment please.",
            "CUSTOMER_CARE",
        )

    if reason and reason.strip():
        conv.write_metric("CANCEL_REASON", reason.strip()[:100])
    conv.write_metric("CANCEL_APPOINTMENT_FLOW_SUCCESSFUL")
    conv.state.selected_appointment_id = ""
    conv.state.task = ""
    visits.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    return "Cancelled. Tell the caller the visit is cancelled, then ask if there's anything else."
