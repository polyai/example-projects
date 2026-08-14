"""Called when the caller accepts an offered appointment slot."""

from _gen import *  # <AUTO GENERATED>
import plog
from functions.get_grace_nextgen_api_handler import (
    NextGenHttpError,
    get_grace_nextgen_api_handler,
)
from functions.handoff import handoff
from functions.nextgen_request_models import AppointmentCreateRequest
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import format_slot_display

_SLOT_KEY_BY_NUMBER = {
    1: "booking_offered_slot_1",
    2: "booking_offered_slot_2",
    3: "booking_offered_slot_3",
}


@func_description(
    "Called when the caller accepts one of the offered appointment slots and wants to book it."
)
@func_parameter("slot_number", "Which offered slot the caller accepted: 1, 2, or 3.")
def booking_slot_accepted(conv: Conversation, flow: Flow, slot_number: int):
    """Validate the selected slot, call create_appointment, and confirm."""
    log_prefix = "[booking_slot_accepted]: "
    plog.info(f"{log_prefix} slot_number={slot_number}")

    # Resolve the selected slot from state
    slot_key = _SLOT_KEY_BY_NUMBER.get(int(slot_number), "booking_offered_slot_1")
    offered_slot_data = getattr(conv.state, slot_key, None)
    if not offered_slot_data:
        offered_slot_data = getattr(conv.state, "booking_offered_slot_1", None)

    if not offered_slot_data:
        plog.info(f"{log_prefix} no offered slot data; handing off")
        return handoff(
            conv,
            reason="BOOKING_SLOT_DATA_MISSING",
            utterance="We couldn't complete the booking. Let me transfer you to someone who can help.",
        )

    slot = AppointmentSlot.model_validate(offered_slot_data)

    # Resolve patient ID
    identified = getattr(conv.state, "identified_patient", None)
    person_id = identified.get("id") if isinstance(identified, dict) else None
    if not person_id:
        plog.info(f"{log_prefix} no patient id; handing off")
        return handoff(
            conv,
            reason="BOOKING_NO_PATIENT_ID",
            utterance="We couldn't complete the booking. Let me transfer you to someone who can help.",
        )

    # Build resource IDs
    resource_ids: list[str] = []
    if slot.resource_ids:
        resource_ids = [str(r) for r in slot.resource_ids]
    elif slot.resource_id:
        resource_ids = [str(slot.resource_id)]

    event_id = str(slot.event_id) if slot.event_id else ""

    raw_details = getattr(conv.state, "booking_appointment_details", None) or ""
    appointment_details = (
        f"(polysa) {raw_details}".strip() if raw_details else "(polysa)"
    )

    # Create the appointment
    try:
        handler = get_grace_nextgen_api_handler(conv)
        create_payload: dict = {
            "PersonId": str(person_id),
            "EventId": event_id,
            "LocationId": str(slot.location_id or ""),
            "ResourceIds": resource_ids,
            "AppointmentDate": str(slot.start_date),
            "DurationMinutes": int(slot.duration_minutes or 15),
            "Details": appointment_details,
        }
        result = handler.create_appointment(
            AppointmentCreateRequest.model_validate(create_payload)
        )
    except (NextGenHttpError, Exception) as e:
        plog.info(f"{log_prefix} create_appointment failed error='{e}'")
        conv.write_metric("BOOKING_FLOW_API_ERROR", True)
        return handoff(
            conv,
            reason="BOOKING_API_ERROR",
            utterance="We ran into an issue booking that appointment. Let me transfer you to someone who can help.",
        )

    booked_id = (result.appointment_id or result.id) if result else None
    conv.state.booking_confirmed_appointment_id = str(booked_id) if booked_id else None

    slot_display = format_slot_display(slot)
    conv.write_metric("BOOKING_FLOW_APPOINTMENT_BOOKED", True)
    conv.write_metric("BOOKING_FLOW_COMPLETED", True)
    plog.info(f"{log_prefix} appointment booked successfully")

    conv.exit_flow()
    return {
        "utterance": (
            f"You're all set! Your appointment is confirmed for {slot_display}. "
            "Is there anything else I can help you with?"
        )
    }
