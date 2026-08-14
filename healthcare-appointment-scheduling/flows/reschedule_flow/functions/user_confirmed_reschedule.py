from _gen import *  # <AUTO GENERATED>
from functions.extract_time_preference import extract_time_preference_from_conversation
from functions.fetch_available_slots import fetch_available_slots_for_state
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import (
    format_slot_display,
    get_next_available_slot,
    select_closest_slot,
)


@func_description(
    "Called when the user confirms the appointment they want to reschedule."
)
def user_confirmed_reschedule(conv: Conversation, flow: Flow):
    appointment_id = getattr(conv.state, "reschedule_target_appointment_id", None)
    if not appointment_id:
        conv.exit_flow()
        return {
            "utterance": "We couldn't complete the rescheduling. Please try again later."
        }

    conv.write_metric("RESCHEDULE_FLOW_APPOINTMENT_CONFIRMED", True)

    preload = fetch_available_slots_for_state(conv)
    if not preload.ok:
        conv.exit_flow()
        return {"utterance": preload.utterance}

    raw_slots = getattr(conv.state, "reschedule_available_slots", None) or []
    slots = [AppointmentSlot.model_validate(s) for s in raw_slots]

    pref = extract_time_preference_from_conversation(conv)
    if pref.has_preference:
        offered = select_closest_slot(
            requested_date=pref.requested_date,
            requested_time=pref.requested_time,
            slots=slots,
        )
        if offered is None:
            offered = get_next_available_slot(slots)
    else:
        offered = get_next_available_slot(slots)

    if offered is None:
        conv.exit_flow()
        return {
            "utterance": (
                "I'm not finding any available times right now. "
                "Let me transfer you to someone who can help."
            )
        }

    conv.state.reschedule_offered_slot = offered.model_dump(mode="json")
    conv.state.reschedule_declined_slot_starts = []
    conv.state.reschedule_offered_slot_display = format_slot_display(offered)
    conv.write_metric("RESCHEDULE_FLOW_SLOT_OFFERED", True)

    flow.goto_step("Offer Slot")
    display = conv.state.reschedule_offered_slot_display
    return {"utterance": f"I have an opening on {display}. Does that work for you?"}
