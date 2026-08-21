"""Called when the caller confirms an appointment type; fetches slots and offers the first two."""

import plog

from _gen import *  # <AUTO GENERATED>
from functions.fetch_available_slots import fetch_booking_slots_for_state
from functions.handoff import handoff
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import (
    format_slot_offer_display,
    get_top_n_available_slots,
)


@func_description(
    "Called when the caller confirms the appointment type. Fetches available slots and offers the best two options."
)
@func_parameter(
    "appointment_type",
    "The type of appointment to book: 'ill', 'recheck', or 'wellness'.",
)
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=3,
    delay_responses=[("One moment.", 2), ("Just looking that up now.", 3)],
)
def appointment_type_confirmed(conv: Conversation, flow: Flow, appointment_type: str):
    """Fetch available slots for the chosen appointment type and offer two options."""
    log_prefix = "[appointment_type_confirmed]: "
    plog.info(f"{log_prefix} appointment_type='{appointment_type}'")

    # The LLM supplies appointment_type, so normalise the case once here: the
    # BOOKING_FLOW_TYPE_CONFIRMED metric declares lowercase values, and the
    # _APPOINTMENT_TYPE_LABELS lookup below is keyed lowercase too.
    appointment_type = (appointment_type or "").lower()

    conv.state.booking_appointment_type = appointment_type
    if appointment_type:
        conv.write_metric("BOOKING_FLOW_TYPE_CONFIRMED", appointment_type)

    _APPOINTMENT_TYPE_LABELS = {
        "recheck": "Follow-up",
        "ill": "Sick visit",
        "wellness": "Wellness check",
    }
    conv.state.booking_appointment_details = _APPOINTMENT_TYPE_LABELS.get(
        appointment_type, appointment_type
    )

    # Fetch available slots into state
    fetch_result = fetch_booking_slots_for_state(conv)
    if not fetch_result.ok:
        plog.info(f"{log_prefix} slot fetch failed; handing off")
        return handoff(
            conv,
            reason="BOOKING_NO_SLOTS_AVAILABLE",
            utterance="I'm not able to look up available times right now. Let me transfer you to someone who can help.",
        )

    raw_slots = getattr(conv.state, "booking_available_slots", None) or []
    all_slots = [AppointmentSlot.model_validate(s) for s in raw_slots]

    offered = get_top_n_available_slots(all_slots, n=2)

    if not offered:
        plog.info(f"{log_prefix} no slots available; handing off")
        return handoff(
            conv,
            reason="BOOKING_NO_SLOTS_AVAILABLE",
            utterance="I'm not seeing any available appointment times right now. Let me transfer you to someone who can help.",
        )

    # Store offered slots in state
    conv.state.booking_offered_slot_1 = offered[0].model_dump(mode="json")
    conv.state.booking_offered_slot_2 = (
        offered[1].model_dump(mode="json") if len(offered) > 1 else None
    )
    conv.state.booking_offered_slot_3 = None

    slots_display = format_slot_offer_display(offered)
    conv.state.booking_offered_slots_display = slots_display
    conv.write_metric("BOOKING_FLOW_SLOTS_OFFERED", True)

    plog.info(f"{log_prefix} offering display='{slots_display[:80]}'", is_pii=True)

    flow.goto_step("Offer Booking Slot")
    return {
        "utterance": f"Alright, I'm seeing {slots_display}. Would one of those work for you?"
    }
