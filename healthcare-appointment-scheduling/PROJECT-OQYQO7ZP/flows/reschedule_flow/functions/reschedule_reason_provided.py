from typing import Any

import plog
from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import EVENT_ID_BY_APPOINTMENT_TYPE, FOLLOW_UP_EVENT_ID
from functions.get_grace_nextgen_api_handler import get_grace_nextgen_api_handler
from functions.handoff import handoff
from functions.nextgen_request_models import AppointmentPatchRequest, AppointmentRescheduleRequest
from functions.nextgen_response_models import AppointmentSlot, ListItem


def _select_reschedule_reason_id(
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

    if not user_reason.strip():
        fallback_id = _other_or_first_id()
        plog.info(
            f"{log_prefix} no user reason provided; using fallback "
            f"id_last4='{str(fallback_id)[-4:] if fallback_id and len(str(fallback_id)) >= 4 else 'none'}'"
        )
        return fallback_id

    numbered = "\n".join(f"{i + 1}. {r.name or '(unnamed)'}" for i, r in enumerate(reasons))
    prompt = (
        "You are matching a patient's stated rescheduling reason to the closest option "
        "from a predefined list.\n\n"
        f"Patient's stated reason: {user_reason!r}\n\n"
        f"Available rescheduling reasons:\n{numbered}\n\n"
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
                f"id_last4='{str(matched_id)[-4:] if len(str(matched_id)) >= 4 else '****'}'"
            )
            return matched_id
    except Exception as e:
        conv.log.error("reschedule_reason_provided: prompt_llm matching failed", error=str(e))
        plog.info(f"{log_prefix} prompt_llm matching failed error='{e}'; using fallback")

    fallback_id = _other_or_first_id()
    plog.info(
        f"{log_prefix} using fallback reason "
        f"id_last4='{str(fallback_id)[-4:] if fallback_id and len(str(fallback_id)) >= 4 else 'none'}'"
    )
    return fallback_id


@func_description("Store the user's rescheduling reason and execute the appointment reschedule.")
@func_parameter(
    "rescheduling_reason",
    "The reason the user gave for rescheduling their appointment, in their own words. Pass an empty string if they declined to give a reason.",
)
def reschedule_reason_provided(
    conv: Conversation, flow: Flow, rescheduling_reason: str
) -> dict[str, Any]:
    """Match user's reason to the closest API reschedule reason, then reschedule."""
    log_prefix = "[reschedule_reason_provided.reschedule_reason_provided]: "
    plog.info(f"{log_prefix} rescheduling_reason_length={len(rescheduling_reason)}")

    appointment_id = getattr(conv.state, "reschedule_target_appointment_id", None)
    ap_last4 = (
        str(appointment_id)[-4:] if appointment_id and len(str(appointment_id)) >= 4 else "none"
    )
    plog.info(f"{log_prefix} reschedule_target_appointment_id_last4={ap_last4!r}")

    if not appointment_id:
        plog.info(f"{log_prefix} missing reschedule_target_appointment_id; exiting")
        conv.log.error("reschedule_reason_provided: no reschedule_target_appointment_id")
        conv.exit_flow()
        return {"utterance": "We couldn't complete the rescheduling. Please try again later."}

    offered_slot_data = getattr(conv.state, "reschedule_offered_slot", None)
    if not offered_slot_data:
        plog.info(f"{log_prefix} missing reschedule_offered_slot; exiting")
        conv.log.error("reschedule_reason_provided: no reschedule_offered_slot on state")
        conv.exit_flow()
        return {"utterance": "We couldn't complete the rescheduling. Please try again later."}

    slot = AppointmentSlot.model_validate(offered_slot_data)
    plog.info(
        f"{log_prefix} slot_start='{slot.start_date}' duration={slot.duration_minutes}",
        is_pii=True,
    )

    try:
        handler = get_grace_nextgen_api_handler(conv)
        reasons = handler.get_reschedule_reasons()
    except Exception as e:
        plog.info(f"{log_prefix} get_reschedule_reasons failed error='{e}'")
        conv.log.error("reschedule_reason_provided: get_reschedule_reasons failed", error=str(e))
        conv.write_metric("RESCHEDULE_FLOW_API_ERROR")
        conv.exit_flow()
        return {
            "utterance": (
                "We couldn't complete the rescheduling right now. Please try again later."
            )
        }

    plog.info(f"{log_prefix} reschedule_reasons_count={len(reasons)}")

    reschedule_reason_id = _select_reschedule_reason_id(
        conv, rescheduling_reason, reasons, log_prefix
    )

    if not reschedule_reason_id:
        plog.info(f"{log_prefix} no reschedule_reason_id resolved; exiting")
        conv.log.error("reschedule_reason_provided: no reschedule reasons from API")
        conv.exit_flow()
        return {
            "utterance": (
                "We couldn't complete the rescheduling right now. Please try again later."
            )
        }

    resource_ids: list[str] | None = None
    if slot.resource_ids:
        resource_ids = slot.resource_ids
    elif slot.resource_id:
        resource_ids = [slot.resource_id]

    # Use the original appointment's event_id to preserve the appointment type.
    # Fall back to FOLLOW_UP_EVENT_ID if the stored event_id is absent or unrecognised.
    _known_ids = {v.lower() for v in EVENT_ID_BY_APPOINTMENT_TYPE.values()}
    _target_event_id = getattr(conv.state, "reschedule_target_event_id", None) or ""
    event_id = _target_event_id if _target_event_id.lower() in _known_ids else FOLLOW_UP_EVENT_ID
    plog.info(f"{log_prefix} using event_id='{event_id}' (target='{_target_event_id}')")

    payload_data: dict = {
        "AppointmentDate": str(slot.start_date),
        "DurationMinutes": slot.duration_minutes,
        "EventId": event_id,
        "RescheduleReasonId": reschedule_reason_id,
    }
    if slot.location_id:
        payload_data["LocationId"] = slot.location_id
    if resource_ids:
        payload_data["ResourceIds"] = resource_ids

    try:
        reschedule_payload = AppointmentRescheduleRequest.model_validate(payload_data)
        result = handler.reschedule_appointment(str(appointment_id), reschedule_payload)
    except Exception as e:
        plog.info(f"{log_prefix} reschedule_appointment failed error='{e}'")
        conv.log.error("reschedule_reason_provided: reschedule_appointment failed", error=str(e))
        conv.write_metric("RESCHEDULE_FLOW_API_ERROR")
        is_cm = getattr(conv.state, "caller_is_case_manager", False)
        return handoff(
            conv,
            reason="RESCHEDULE_API_ERROR",
            utterance=(
                "We ran into an issue rescheduling the appointment. "
                "Let me transfer you to someone who can help."
                if is_cm
                else "We ran into an issue rescheduling your appointment. "
                "Let me transfer you to someone who can help."
            ),
        )

    if result is None:
        # API returns an empty body on successful reschedule — treat as success.
        plog.info(
            f"{log_prefix} reschedule_appointment returned None (empty body); treating as success"
        )
        conv.log.info(
            "reschedule_reason_provided: reschedule_appointment returned None "
            "(likely empty 200/204 body — treating as success)"
        )

    # Patch the new appointment's details to prepend (polyra).
    # Find the newly created rescheduled appointment, read its details, and patch.
    try:
        identified = getattr(conv.state, "identified_patient", None)
        person_id = identified.get("id") if isinstance(identified, dict) else None
        if person_id:
            new_appt = handler.find_person_rescheduled_appointment(
                person_id=person_id,
                original_appointment_id=str(appointment_id),
                end_date_iso=str(slot.start_date)[:10] if slot.start_date else "",
            )
            if new_appt:
                new_appt_id = new_appt.appointment_id or new_appt.id
                existing_details = new_appt.details or ""
                patched_details = (
                    f"(polyra) {existing_details}".strip() if existing_details else "(polyra)"
                )
                handler.patch_appointment(
                    str(new_appt_id),
                    AppointmentPatchRequest.model_validate({"Details": patched_details}),
                )
                plog.info(
                    f"{log_prefix} patched new appointment details with (polyra) "
                    f"new_appt_id_last4='{str(new_appt_id)[-4:]}'"
                )
            else:
                plog.info(f"{log_prefix} could not find rescheduled appointment to patch details")
        else:
            plog.info(f"{log_prefix} no person_id; skipping (polyra) details patch")
    except Exception as e:
        plog.info(f"{log_prefix} (polyra) details patch failed error='{e}'")
        conv.log.error("reschedule_reason_provided: details patch failed", error=str(e))

    _slot_str = str(slot.start_date) if slot.start_date else ""
    conv.write_metric("RESCHEDULE_FLOW_APPOINTMENT_DATE", _slot_str[:10] if _slot_str else None)
    conv.write_metric(
        "RESCHEDULE_FLOW_APPOINTMENT_TIME", _slot_str[11:16] if len(_slot_str) > 10 else None
    )
    conv.write_metric("RESCHEDULE_FLOW_COMPLETED")
    conv.log.info(
        "Reschedule flow: appointment successfully rescheduled",
        appointment_id_last4=ap_last4,
        new_slot_start=str(slot.start_date),
        is_pii=True,
    )
    plog.info(f"{log_prefix} reschedule successful new_slot_start='{slot.start_date}'", is_pii=True)

    display = getattr(conv.state, "reschedule_offered_slot_display", "your new time")
    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    conv.exit_flow()
    if is_cm:
        return {
            "utterance": (
                f"The appointment has been rescheduled to {display}. "
                "Is there anything else I can help you with?"
            )
        }
    return {
        "utterance": (
            f"Your appointment has been rescheduled to {display}. "
            "Is there anything else I can help you with?"
        )
    }
