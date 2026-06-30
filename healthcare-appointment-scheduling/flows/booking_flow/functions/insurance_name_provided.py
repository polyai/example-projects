import plog
from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


def is_not_accepted(plan_name: str) -> tuple[bool, str | None]:
    """Stub: all insurance plans are accepted in the template."""
    return (False, None)


def find_closest_accepted_plan_with_llm(conv, insurance_name: str) -> str | None:
    """Stub: no LLM-based plan matching in the template."""
    return insurance_name


def find_closest_accepted_plan_with_difflib(insurance_name: str) -> str | None:
    """Stub: no difflib-based plan matching in the template."""
    return insurance_name


_LOG_PREFIX = "[insurance_name_provided]: "


_SLIDING_FEE_PATTERNS = {
    "sliding fee",
    "sliding scale",
    "sliding fee discount",
    "self pay",
    "self-pay",
}


@func_description(
    "Called when the caller provides their insurance plan name. Matches it against accepted plans and routes accordingly."
)
@func_parameter("insurance_name", "The insurance plan name exactly as spoken by the caller.")
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=2,
    delay_responses=[("typing_noise_short", 1)],
)
def insurance_name_provided(conv: Conversation, flow: Flow, insurance_name: str) -> dict:
    conv.state.insurance_caller_stated = insurance_name
    plog.info(f"{_LOG_PREFIX} caller stated: '{insurance_name}'", is_pii=True)

    lower = insurance_name.strip().lower()
    if any(pat in lower for pat in _SLIDING_FEE_PATTERNS):
        plog.info(f"{_LOG_PREFIX} sliding fee / self-pay detected; continuing booking")
        conv.state.insurance_verified_plan = "Sliding Fee Discount"
        conv.write_metric("INSURANCE_ACCEPTED")
        flow.goto_step("Collect Appointment Event Type")
        return {"content": "Ask the caller what type of appointment they would like to book."}

    rejected, matched_name = is_not_accepted(insurance_name)
    if rejected:
        plog.info(f"{_LOG_PREFIX} direct not-accepted match: '{matched_name}'", is_pii=True)
        conv.write_metric("INSURANCE_NOT_ACCEPTED", matched_name)
        return handoff(
            conv,
            reason="INSURANCE_NOT_ACCEPTED",
            utterance=(
                "Unfortunately, we're not currently accepting that insurance plan for scheduling. "
                "Let me transfer you to our patient accounts team who can assist you further. "
                "Putting you through now."
            ),
        )

    matched = None
    try:
        matched = find_closest_accepted_plan_with_llm(conv, insurance_name)
        plog.info(f"{_LOG_PREFIX} LLM match result: '{matched}'", is_pii=True)
    except Exception as e:
        plog.info(f"{_LOG_PREFIX} LLM match failed: '{e}'")
        conv.log.warning("Insurance LLM match failed", error=str(e))

    if not matched:
        matched = find_closest_accepted_plan_with_difflib(insurance_name)
        plog.info(f"{_LOG_PREFIX} difflib match result: '{matched}'", is_pii=True)

    if not matched:
        attempts = (getattr(conv.state, "insurance_collection_attempts", None) or 0) + 1
        conv.state.insurance_collection_attempts = attempts
        plog.info(f"{_LOG_PREFIX} no match; attempt {attempts}")
        if attempts >= 2:
            conv.write_metric("INSURANCE_MATCH_FAILED_MAX_ATTEMPTS")
            return handoff(
                conv,
                reason="INSURANCE_NOT_ACCEPTED",
                utterance=(
                    "I'm having trouble finding that plan in our system. "
                    "Let me transfer you to our patient accounts team who can verify your coverage. "
                    "Putting you through now."
                ),
            )
        flow.goto_step("Collect Insurance Name")
        return {
            "utterance": (
                "I wasn't able to find that plan in our system. "
                "Could you repeat your insurance plan name?"
            )
        }

    rejected, reject_name = is_not_accepted(matched)
    if rejected:
        plog.info(f"{_LOG_PREFIX} matched plan not accepted: '{reject_name}'", is_pii=True)
        conv.write_metric("INSURANCE_NOT_ACCEPTED", reject_name)
        return handoff(
            conv,
            reason="INSURANCE_NOT_ACCEPTED",
            utterance=(
                "Unfortunately, we're not currently accepting that insurance plan for scheduling. "
                "Let me transfer you to our patient accounts team who can assist you further. "
                "Putting you through now."
            ),
        )

    conv.state.insurance_matched_plan_name = matched
    conv.write_metric("INSURANCE_FUZZY_MATCHED", matched)
    plog.info(f"{_LOG_PREFIX} offering match confirmation: '{matched}'", is_pii=True)
    flow.goto_step("Confirm Insurance Match")

    spoken_lower = insurance_name.strip().lower()
    matched_lower = matched.lower()
    exact_enough = spoken_lower == matched_lower or spoken_lower in matched_lower

    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    if exact_enough:
        if is_cm:
            return {"utterance": f"That was {matched}, right?"}
        return {"utterance": f"That was {matched}, right?"}
    if is_cm:
        return {
            "utterance": f"The closest plan I have is {matched}. Is that the patient's insurance?"
        }
    return {"utterance": f"The closest plan I have is {matched}. Is that right?"}
