from _gen import *  # <AUTO GENERATED>
import re
from datetime import datetime, time

import functions.api_client as api_client
import functions.idnv as idnv
import functions.visits as visits
from functions.handoff import handoff
from functions.utils import site_timezone, variant_attr

READBACK_KEY = "cancel"
SWITCHED_OFF = (
    "For cancellations I'll need to put you through to the team. One moment, please."
)


def _fields(conv, visit) -> list[tuple[str, str]]:
    if not visit:
        return [("visit", "")]
    return [("visit", f"{visit['id']} {visit['date']} {visit['start']}")]


def hours_until(conv, visit: dict) -> float | None:
    """Hours from now until the visit's window starts, in the site's timezone."""
    try:
        _, tz = site_timezone(conv)
        now = conv.state.datetime_now
        if not isinstance(now, datetime):
            return None  # start_function sets it on every call
        now = now.astimezone(tz)
        hour, minute = (int(x) for x in visit["start"].split(":"))
        starts = datetime.combine(
            datetime.fromisoformat(visit["date"]).date(), time(hour, minute), tzinfo=tz
        )
        return round((starts - now).total_seconds() / 3600, 1)
    except Exception:
        conv.log.warning("Could not work out the hours until the visit", exc_info=True)
        return None


def policy_terms(policy: str) -> tuple[float, str] | None:
    """The notice period and the fee from the cancellation policy, e.g. (24, "$50 trip fee")
    from "...for free up to 24 hours before your visit. Later cancellations are charged a $50
    trip fee." None when the policy names no notice in hours or no fee."""
    notice = re.search(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?)\b", policy or "", re.I)
    days = re.search(r"(\d+)\s*days?\b", policy or "", re.I)
    fee = re.search(
        r"(\$\d+(?:\.\d{2})?(?:\s+[a-z-]+){0,2}?\s*fee)", policy or "", re.I
    )
    if not fee or not (notice or days):
        return None
    hours = float(notice.group(1)) if notice else float(days.group(1)) * 24
    return hours, fee.group(1)


def fee_sentence(conv, visit: dict) -> str:
    """The fee sentence, decided in code: only when the visit starts inside the policy's
    notice period. "" otherwise."""
    terms = policy_terms(variant_attr(conv, "cancellation_policy_info"))
    hours = hours_until(conv, visit)
    if not terms or hours is None or not 0 <= hours < terms[0]:
        return ""
    notice, fee = terms
    return (
        f"Just so you know, as it's less than {notice:g} hours away, there's a {fee}."
    )


def cancel_question(conv, visit: dict) -> str:
    """The readback and its question, with the fee sentence when the policy applies."""
    said = f"You've got {visits.describe_visit(visit, conv)}."
    fee = fee_sentence(conv, visit)
    if fee:
        return f"{said} {fee} Shall I still cancel it for you?"
    return f"{said} Shall I cancel that for you?"


def cancel_readback(conv) -> str:
    """The cancellation readback: the whole visit, the fee sentence when the policy charges one
    at this notice, then the question."""
    visit = visits.selected_visit(conv)
    visits.readback_text(conv, READBACK_KEY, _fields(conv, visit))
    visits.mark_question(conv, READBACK_KEY)  # asked again every time
    return (
        f'NOT CANCELLED YET. Say exactly: "{cancel_question(conv, visit)}" Then wait for the '
        "answer. Never ask why they're cancelling.\n\n"
        + visits.call_state(
            conv,
            ["Task: cancel a visit", f"Visit: {visits.describe_visit(visit, conv)}"],
            "Wait for the caller's answer to cancelling it.",
        )
    )


def cancellation_enabled(conv) -> bool:
    settings = (conv.real_time_config or {}).get("settings", {})
    return bool(settings.get("cancel_appointment_flow_enabled", True))


@func_description(
    "Cancel the visit you read back, once the caller has agreed to the cancel question this tool's readback asked."
)
@func_parameter(
    "caller_confirmed",
    "'true' only if the caller's latest reply agreed to the readback question this tool returned. 'Okay', 'sure', 'yes please' or 'go on' to that question is agreement; an answer to something else, a question back or real hesitation is not. Otherwise 'false'.",
)
@func_parameter(
    "reason", "Why they're cancelling, if they offered it. Empty string otherwise."
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Cancelling that for you now.", 3), ("Nearly there.", 3)],
)
def cancel_visit(conv: Conversation, flow: Flow, caller_confirmed: str, reason: str):
    if not idnv.is_verified(conv):
        return idnv.require(conv, "cancel_appointment")
    if not cancellation_enabled(conv):
        return handoff(conv, "CANCEL_APPOINTMENT", SWITCHED_OFF, "CUSTOMER_CARE")
    visit = visits.selected_visit(conv)
    if not visit:
        return (
            "NOT CANCELLED: first find out which visit they want to cancel, then call "
            "choose_visit with its date."
        )
    if not visits.readback_is_current(conv, READBACK_KEY, _fields(conv, visit)):
        return cancel_readback(conv)
    if str(caller_confirmed).strip().lower() != "true":
        return visits.ask_again(conv, READBACK_KEY, cancel_question(conv, visit))
    if visits.same_turn_as_question(conv, READBACK_KEY):
        return visits.ask_again(conv, READBACK_KEY, cancel_question(conv, visit))

    try:
        api_client.cancel_appointment(conv, visit["id"], (reason or "").strip())
    except Exception:
        conv.log.error("cancel_appointment failed", exc_info=True)
        return handoff(
            conv,
            "CANCEL_APPOINTMENT_FAIL",
            "I'm sorry, I couldn't cancel that just now. Let me put you through to the team, who "
            "can. One moment, please.",
            "CUSTOMER_CARE",
        )

    if reason and reason.strip():
        conv.write_metric("CANCEL_REASON", reason.strip()[:100])
    conv.write_metric("CANCEL_APPOINTMENT_FLOW_SUCCESSFUL")
    day = visits.short_day(visit["date"], visits.today(conv))
    conv.state.selected_appointment_id = ""
    conv.state.task = ""
    visits.forget_readback(conv, READBACK_KEY)
    conv.exit_flow()
    return {
        "utterance": f"I've cancelled your visit for {day}. Is there anything else I can help with?"
    }
