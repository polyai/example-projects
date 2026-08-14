from _gen import *  # <AUTO GENERATED>
import plog
from functions.appointment_selection import is_follow_up_appointment
from functions.get_grace_nextgen_api_handler import get_grace_nextgen_api_handler
from functions.handoff import handoff
from functions.nextgen_response_models import ListItem


def _select_cancel_reason_id(
    conv: Conversation,
    user_reason: str,
    reasons: list[ListItem],
    log_prefix: str,
) -> str | None:
    """Use prompt_llm to match user_reason to the closest item in reasons.

    Falls back to the first 'other'-named reason if matching fails, then to
    the first reason overall.
    """
    if not reasons:
        return None

    def _other_or_first_id() -> str | None:
        other = next(
            (r.id for r in reasons if r.name and "other" in r.name.lower() and r.id),
            None,
        )
        return other or next((r.id for r in reasons if r.id), None)

    numbered = "\n".join(
        f"{i + 1}. {r.name or '(unnamed)'}" for i, r in enumerate(reasons)
    )
    prompt = (
        "You are matching a patient's stated cancellation reason to the closest option "
        "from a predefined list.\n\n"
        f"Patient's stated reason: {user_reason!r}\n\n"
        f"Available cancellation reasons:\n{numbered}\n\n"
        "Choose the number of the reason that best matches what the patient said. "
        "If no reason fits well, or the patient gave no reason, choose the option "
        'labelled "other" (or the closest equivalent). '
        "Return ONLY the number. No other text."
    )

    try:
        result = conv.utils.prompt_llm(prompt, show_history=False)
        idx = int((result or "").strip()) - 1
        if 0 <= idx < len(reasons) and reasons[idx].id:
            matched_id = reasons[idx].id
            plog.info(
                f"{log_prefix} prompt_llm matched reason "
                f"name={reasons[idx].name!r} "
                f"id_last4={str(matched_id)[-4:] if len(str(matched_id)) >= 4 else '****'!r}"
            )
            return matched_id
    except Exception as e:
        conv.log.error(
            "cancel_reason_provided: prompt_llm matching failed", error=str(e)
        )
        plog.info(
            f"{log_prefix} prompt_llm matching failed error='{e}'; using fallback"
        )

    fallback_id = _other_or_first_id()
    plog.info(
        f"{log_prefix} using fallback reason "
        f"id_last4={str(fallback_id)[-4:] if fallback_id and len(str(fallback_id)) >= 4 else 'none'!r}"
    )
    return fallback_id


@func_description(
    "Store the user's cancellation reason and execute the appointment cancellation."
)
@func_parameter(
    "cancellation_reason",
    "The reason the user gave for cancelling their appointment, in their own words. Pass an empty string if they declined to give a reason.",
)
def cancel_reason_provided(conv: Conversation, flow: Flow, cancellation_reason: str):
    """Store user's stated reason, match it to the closest API cancel reason, then cancel."""
    log_prefix = "[cancel_reason_provided.cancel_reason_provided]: "

    conv.state.cancel_user_reason = cancellation_reason
    plog.info(
        f"{log_prefix} stored cancel_user_reason length={len(cancellation_reason)}"
    )

    appointment_id = getattr(conv.state, "cancel_target_appointment_id", None)
    ap_last4 = (
        str(appointment_id)[-4:]
        if appointment_id and len(str(appointment_id)) >= 4
        else "none"
    )
    plog.info(f"{log_prefix} cancel_target_appointment_id_last4={ap_last4!r}")

    if not appointment_id:
        plog.info(f"{log_prefix} missing cancel_target_appointment_id; exiting")
        conv.log.error("cancel_reason_provided: no cancel_target_appointment_id")
        conv.exit_flow()
        return {
            "utterance": "We couldn't complete the cancellation. Please try again later."
        }

    try:
        handler = get_grace_nextgen_api_handler(conv)
        current = handler.get_appointment(str(appointment_id))
    except Exception as e:
        plog.info(f"{log_prefix} get_appointment failed error='{e}'")
        conv.log.error("cancel_reason_provided: get_appointment failed", error=str(e))
        conv.write_metric("CANCEL_FLOW_API_ERROR", True)
        conv.exit_flow()
        return {
            "utterance": (
                "We couldn't complete the cancellation right now. Please try again later."
            )
        }

    if current is None:
        plog.info(
            f"{log_prefix} get_appointment returned None; cannot verify visit type"
        )
        conv.log.error("cancel_reason_provided: get_appointment returned None")
        conv.exit_flow()
        return {
            "utterance": (
                "We couldn't complete the cancellation right now. Please try again later."
            )
        }

    if not is_follow_up_appointment(current):
        plog.info(
            f"{log_prefix} execute guard: not follow-up event_id='{current.event_id}' "
            "handoff CANCEL_NON_FOLLOW_UP"
        )
        conv.write_metric("CANCEL_OOS", True)
        return handoff(
            conv,
            reason="CANCEL_NON_FOLLOW_UP",
            utterance="That type of visit can't be cancelled on this line. I'll transfer you to someone who can help.",
        )

    if current.is_rescheduled is True:
        plog.info(
            f"{log_prefix} execute guard: appointment already rescheduled; "
            "handoff CANCEL_ALREADY_RESCHEDULED"
        )
        conv.write_metric("CANCEL_FLOW_ALREADY_RESCHEDULED", True)
        return handoff(
            conv,
            reason="CANCEL_ALREADY_RESCHEDULED",
            utterance=(
                "That appointment has already been rescheduled, so I can't cancel it "
                "from here. Let me transfer you to someone who can help."
            ),
        )

    try:
        reasons = handler.get_cancel_reasons()
    except Exception as e:
        plog.info(f"{log_prefix} get_cancel_reasons failed error='{e}'")
        conv.log.error(
            "cancel_reason_provided: get_cancel_reasons failed", error=str(e)
        )
        conv.write_metric("CANCEL_FLOW_API_ERROR", True)
        conv.exit_flow()
        return {
            "utterance": (
                "We couldn't complete the cancellation right now. Please try again later."
            )
        }

    plog.info(f"{log_prefix} cancel_reasons_count={len(reasons)}")

    cancel_reason_id = _select_cancel_reason_id(
        conv, cancellation_reason, reasons, log_prefix
    )

    if not cancel_reason_id:
        plog.info(f"{log_prefix} no cancel_reason_id resolved; exiting")
        conv.log.error("cancel_reason_provided: no cancel reasons from API")
        conv.exit_flow()
        return {
            "utterance": (
                "We couldn't complete the cancellation right now. Please try again later."
            )
        }

    try:
        result = handler.cancel_appointment(
            str(appointment_id),
            str(cancel_reason_id),
        )
    except Exception as e:
        plog.info(f"{log_prefix} cancel_appointment failed error='{e}'")
        conv.log.error(
            "cancel_reason_provided: cancel_appointment failed", error=str(e)
        )
        conv.write_metric("CANCEL_FLOW_API_ERROR", True)
        conv.exit_flow()
        return {
            "utterance": (
                "We couldn't cancel that appointment. Please try again or call the office."
            )
        }

    is_cancelled = result.is_cancelled if result is not None else None
    plog.info(
        f"{log_prefix} cancel_appointment response",
        result_present=result is not None,
        is_cancelled=is_cancelled,
    )

    conv.write_metric("CANCEL_FLOW_COMPLETED", True)
    conv.log.info(
        "Cancel flow: appointment cancelled",
        appointment_id_last4=(
            str(appointment_id)[-4:] if len(str(appointment_id)) >= 4 else "****"
        ),
    )
    conv.exit_flow()

    detail = ""
    if result is not None and result.is_cancelled is True:
        detail = " It's cancelled in our system."
    plog.info(f"{log_prefix} flow exit after success")
    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    base = (
        "I've cancelled that appointment."
        if is_cm
        else "I've cancelled that appointment for you."
    )
    return {"utterance": base + detail + " Is there anything else I can help with?"}
