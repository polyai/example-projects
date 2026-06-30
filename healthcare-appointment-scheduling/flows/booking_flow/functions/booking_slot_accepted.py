import plog
from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import EVENT_ID_BY_APPOINTMENT_TYPE, FOLLOW_UP_EVENT_ID
from functions.get_grace_nextgen_api_handler import NextGenHttpError, get_grace_nextgen_api_handler
from functions.handoff import handoff
from functions.nextgen_request_models import AppointmentCreateRequest
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import format_slot_display

_SLOT_KEY_BY_NUMBER = {
    1: "booking_offered_slot_1",
    2: "booking_offered_slot_2",
    3: "booking_offered_slot_3",
}

_LANGUAGE_LINE_RESOURCE_ID = "6c697a3a-4b27-4e18-97ad-855c20c84a1c"


@func_description(
    "Called when the caller accepts one of the offered appointment slots and wants to book it. slot_number is 1, 2, or 3 depending on which offered slot they chose."
)
@func_parameter(
    "slot_number",
    "Which offered slot the caller accepted: 1 for the first slot, 2 for the second, 3 for the third.",
)
def booking_slot_accepted(conv: Conversation, flow: Flow, slot_number: int):
    """Validate the selected slot, call create_appointment, and confirm with the caller."""
    log_prefix = "[booking_slot_accepted.booking_slot_accepted]: "
    plog.info(f"{log_prefix} slot_number={slot_number}")

    # Resolve the selected slot from state
    slot_key = _SLOT_KEY_BY_NUMBER.get(int(slot_number), "booking_offered_slot_1")
    offered_slot_data = getattr(conv.state, slot_key, None)
    if not offered_slot_data:
        plog.info(f"{log_prefix} slot_key='{slot_key}' not in state; falling back to slot 1")
        offered_slot_data = getattr(conv.state, "booking_offered_slot_1", None)

    if not offered_slot_data:
        plog.info(f"{log_prefix} no offered slot data; handing off")
        conv.log.error("booking_slot_accepted: no offered slot data on state")
        return handoff(
            conv,
            reason="BOOKING_SLOT_DATA_MISSING",
            utterance="We couldn't complete the booking. Let me transfer you to someone who can help.",
        )

    slot = AppointmentSlot.model_validate(offered_slot_data)

    # Validate required slot fields
    missing = [
        f
        for f, v in [
            ("start_date", slot.start_date),
            ("location_id", slot.location_id),
            ("duration_minutes", slot.duration_minutes),
        ]
        if not v
    ]
    if missing:
        plog.info(f"{log_prefix} slot missing required fields={missing}; handing off")
        conv.log.error(
            "booking_slot_accepted: selected slot missing required fields", missing=missing
        )
        return handoff(
            conv,
            reason="BOOKING_SLOT_INCOMPLETE",
            utterance="We couldn't complete the booking. Let me transfer you to someone who can help.",
        )

    # Resolve patient ID from identified patient
    identified = getattr(conv.state, "identified_patient", None)
    person_id = identified.get("id") if isinstance(identified, dict) else None
    if not person_id:
        plog.info(f"{log_prefix} no identified_patient or missing id; handing off")
        conv.log.error("booking_slot_accepted: no patient id on state")
        return handoff(
            conv,
            reason="BOOKING_NO_PATIENT_ID",
            utterance="We couldn't complete the booking. Let me transfer you to someone who can help.",
        )

    # Build resource IDs list
    resource_ids: list[str] = []
    if slot.resource_ids:
        resource_ids = [str(r) for r in slot.resource_ids]
    elif slot.resource_id:
        resource_ids = [str(slot.resource_id)]

    if not resource_ids:
        plog.info(f"{log_prefix} no resource IDs on slot; handing off")
        conv.log.error("booking_slot_accepted: no resource_ids or resource_id on slot")
        return handoff(
            conv,
            reason="BOOKING_NO_RESOURCE_ID",
            utterance="We couldn't complete the booking. Let me transfer you to someone who can help.",
        )

    appointment_type = getattr(conv.state, "booking_appointment_type", None) or ""
    event_id = (
        str(slot.event_id)
        if slot.event_id
        else EVENT_ID_BY_APPOINTMENT_TYPE.get(appointment_type, FOLLOW_UP_EVENT_ID)
    )

    slot_display = format_slot_display(slot)
    plog.info(
        f"{log_prefix} booking slot_start='{slot.start_date}' "
        f"location_id='{slot.location_id}' event_id='{event_id}'",
        is_pii=True,
    )

    raw_details = getattr(conv.state, "booking_appointment_details", None) or ""
    appointment_details = f"(polysa) {raw_details}".strip() if raw_details else "(polysa)"

    # Try the selected slot first, then fall back to remaining offered slots on conflict.
    slots_to_try = [slot]
    for fallback_num in range(1, 4):
        if fallback_num == int(slot_number):
            continue
        fb_key = _SLOT_KEY_BY_NUMBER.get(fallback_num)
        fb_data = getattr(conv.state, fb_key, None) if fb_key else None
        if fb_data:
            slots_to_try.append(AppointmentSlot.model_validate(fb_data))

    result = None
    for attempt_idx, attempt_slot in enumerate(slots_to_try):
        attempt_resource_ids: list[str] = []
        if attempt_slot.resource_ids:
            attempt_resource_ids = [str(r) for r in attempt_slot.resource_ids]
        elif attempt_slot.resource_id:
            attempt_resource_ids = [str(attempt_slot.resource_id)]

        if not attempt_resource_ids:
            continue

        if getattr(conv.state, "patient_language_barrier", False):
            if _LANGUAGE_LINE_RESOURCE_ID not in attempt_resource_ids:
                attempt_resource_ids.append(_LANGUAGE_LINE_RESOURCE_ID)

        try:
            handler = get_grace_nextgen_api_handler(conv)

            rendering_provider_id = None
            if attempt_slot.resource_id:
                resource_obj = handler.get_resource(str(attempt_slot.resource_id))
                rendering_provider_id = resource_obj.provider_id if resource_obj else None

            duration = int(attempt_slot.duration_minutes)
            if getattr(conv.state, "patient_needs_extended_appointment", False) and duration < 30:
                plog.info(
                    f"{log_prefix} extended appointment: overriding duration {duration} -> 30"
                )
                duration = 30
            if getattr(conv.state, "patient_language_barrier", False) and duration < 30:
                plog.info(f"{log_prefix} language barrier: overriding duration {duration} -> 30")
                duration = 30

            create_payload: dict = {
                "PersonId": str(person_id),
                "EventId": event_id,
                "LocationId": str(attempt_slot.location_id),
                "ResourceIds": attempt_resource_ids,
                "AppointmentDate": str(attempt_slot.start_date),
                "DurationMinutes": duration,
                "Details": appointment_details,
            }
            if rendering_provider_id:
                create_payload["RenderingProviderId"] = rendering_provider_id

            result = handler.create_appointment(
                AppointmentCreateRequest.model_validate(create_payload)
            )
            # Success — use this slot
            slot = attempt_slot
            slot_display = format_slot_display(slot)
            break
        except NextGenHttpError as e:
            is_conflict = e.status_code == 400 and "already has an appointment" in str(e).lower()
            if is_conflict and attempt_idx < len(slots_to_try) - 1:
                plog.info(
                    f"{log_prefix} slot conflict at '{attempt_slot.start_date}'; "
                    f"retrying with next offered slot",
                    is_pii=True,
                )
                conv.log.info(
                    "booking_slot_accepted: slot conflict, retrying next slot",
                    conflicting_slot=str(attempt_slot.start_date),
                    is_pii=True,
                )
                continue
            plog.info(f"{log_prefix} create_appointment failed error='{e}'")
            conv.log.error(
                "booking_slot_accepted: create_appointment API call failed", error=str(e)
            )
            conv.write_metric("BOOKING_FLOW_API_ERROR")
            return handoff(
                conv,
                reason="BOOKING_API_ERROR",
                utterance="We ran into an issue booking that appointment. Let me transfer you to someone who can help.",
            )
        except Exception as e:
            plog.info(f"{log_prefix} create_appointment failed error='{e}'")
            conv.log.error(
                "booking_slot_accepted: create_appointment API call failed", error=str(e)
            )
            conv.write_metric("BOOKING_FLOW_API_ERROR")
            return handoff(
                conv,
                reason="BOOKING_API_ERROR",
                utterance="We ran into an issue booking that appointment. Let me transfer you to someone who can help.",
            )

    if result is None:
        # API may return an empty body on success (200/201) — treat as success.
        plog.info(
            f"{log_prefix} create_appointment returned None (empty body); treating as success"
        )

    booked_id = (result.appointment_id or result.id) if result else None
    conv.state.booking_confirmed_appointment_id = str(booked_id) if booked_id else None

    _slot_str = str(slot.start_date) if slot.start_date else ""
    conv.write_metric("BOOKING_FLOW_APPOINTMENT_DATE", _slot_str[:10] if _slot_str else None)
    conv.write_metric(
        "BOOKING_FLOW_APPOINTMENT_TIME", _slot_str[11:16] if len(_slot_str) > 10 else None
    )
    conv.write_metric("BOOKING_FLOW_APPOINTMENT_BOOKED")
    conv.write_metric("BOOKING_FLOW_COMPLETED")
    plog.info(
        f"{log_prefix} appointment booked id_last4="
        f"'{str(booked_id)[-4:] if booked_id and len(str(booked_id)) >= 4 else '****'}'"
    )
    conv.log.info(
        "Booking flow: appointment successfully booked",
        slot_start=str(slot.start_date),
        is_pii=True,
    )

    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    booked_appt_type = getattr(conv.state, "booking_appointment_type", None) or ""

    if booked_appt_type == "hospital_follow_up" and not is_cm:
        return handoff(
            conv,
            reason="HOSP_FU_TRANSITIONAL_CARE",
            utterance=(
                f"You're all set! Your appointment is confirmed for {slot_display}. "
                "I'll need to transfer you to a transitional care nurse to review your plan of care and finalize this visit. "
                "Please hold while I transfer you."
            ),
        )

    conv.exit_flow()
    if is_cm:
        return {
            "utterance": (
                f"All set! The appointment is confirmed for {slot_display}. "
                "Is there anything else I can help you with?"
            )
        }
    return {
        "utterance": (
            f"You're all set! Your appointment is confirmed for {slot_display}. "
            "Is there anything else I can help you with?"
        )
    }
