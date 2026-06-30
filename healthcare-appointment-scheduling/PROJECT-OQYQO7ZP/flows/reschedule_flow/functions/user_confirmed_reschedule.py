from datetime import date

import plog
from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import (
    EVENT_ID_BY_APPOINTMENT_TYPE,
    get_recall_window,
    is_recheck_type,
)
from functions.extract_time_preference import extract_time_preference_from_conversation
from functions.fetch_available_slots import fetch_available_slots_for_state
from functions.handoff import handoff
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import (
    format_slot_display,
    get_next_available_slot,
    select_closest_slot,
)

# Reverse mapping: event_id (lowercased) -> appointment type name
_EVENT_ID_TO_TYPE: dict[str, str] = {v.lower(): k for k, v in EVENT_ID_BY_APPOINTMENT_TYPE.items()}


@func_description(
    "Called when the user confirms the appointment they want to reschedule; fetches available slots, applies any time preference, and moves to slot offering."
)
def user_confirmed_reschedule(conv: Conversation, flow: Flow):
    """Confirm the target appointment and begin slot offering."""
    log_prefix = "[user_confirmed_reschedule.user_confirmed_reschedule]: "
    plog.info(f"{log_prefix} flow_current_step={getattr(flow, 'current_step', None)!r}")
    appointment_id = getattr(conv.state, "reschedule_target_appointment_id", None)
    ap_last4 = (
        str(appointment_id)[-4:] if appointment_id and len(str(appointment_id)) >= 4 else "none"
    )
    plog.info(f"{log_prefix} reschedule_target_appointment_id_last4={ap_last4!r}")

    if not appointment_id:
        plog.info(f"{log_prefix} missing reschedule_target_appointment_id; exiting")
        conv.log.error("user_confirmed_reschedule: no reschedule_target_appointment_id")
        conv.exit_flow()
        return {"utterance": "We couldn't complete the rescheduling. Please try again later."}

    conv.write_metric("RESCHEDULE_FLOW_APPOINTMENT_CONFIRMED")
    conv.log.info(
        "Reschedule flow: appointment confirmed for rescheduling",
        appointment_id_last4=str(appointment_id)[-4:] if len(str(appointment_id)) >= 4 else "****",
    )

    # Determine the appointment type from the stored event_id
    target_event_id = getattr(conv.state, "reschedule_target_event_id", None) or ""
    appointment_type = _EVENT_ID_TO_TYPE.get(target_event_id.lower(), "")
    plog.info(
        f"{log_prefix} target_event_id='{target_event_id}' "
        f"resolved_appointment_type='{appointment_type}'"
    )

    # --- Branch A: Hospital/ER follow-up → collect discharge date first ---
    if appointment_type in ("hospital_follow_up", "er_follow_up"):
        conv.state.reschedule_target_appointment_type = appointment_type
        facility_label = (
            "hospital" if appointment_type == "hospital_follow_up" else "emergency room"
        )
        conv.state.reschedule_facility_type_label = facility_label
        conv.state.reschedule_today_date = date.today().isoformat()
        plog.info(f"{log_prefix} hospital/ER follow-up detected; routing to Collect Discharge Date")
        flow.goto_step("Collect Discharge Date")
        is_cm = getattr(conv.state, "caller_is_case_manager", False)
        if is_cm:
            return {
                "utterance": f"Alright, since this is a {facility_label} follow-up, I'll just need to check: when was the patient discharged from the {facility_label}?"
            }
        return {
            "utterance": f"Alright, since this is a {facility_label} follow-up, I'll just need to check: when were you discharged from the {facility_label}?"
        }

    # --- Branch B: Recheck → recall window ---
    start_override = None
    end_override = None
    if is_recheck_type(appointment_type):
        recall = get_recall_window(conv, appointment_type)
        if not recall.ok:
            plog.info(
                f"{log_prefix} no recall found for recheck type '{appointment_type}'; handing off"
            )
            conv.write_metric("RESCHEDULE_NO_RECALL_FOUND")
            return handoff(
                conv,
                reason="RESCHEDULE_NO_RECALL",
                utterance=(
                    "I wasn't able to find a recall record for that type of recheck. "
                    "Let me transfer you to someone who can help reschedule that."
                ),
            )
        start_override = recall.start_iso
        end_override = recall.end_iso
        plog.info(
            f"{log_prefix} recall window: start='{start_override}' end='{end_override}'",
            is_pii=True,
        )

    # --- Branch C: Standard / ill → default 90-day window (no overrides) ---

    # Fetch available follow-up slots
    preload = fetch_available_slots_for_state(
        conv, start_override=start_override, end_override=end_override
    )
    if not preload.ok:
        plog.info(f"{log_prefix} slot fetch failed")
        conv.exit_flow()
        return {"utterance": preload.utterance}

    raw_slots = getattr(conv.state, "reschedule_available_slots", None) or []
    slots = [AppointmentSlot.model_validate(s) for s in raw_slots]
    plog.info(f"{log_prefix} available_slot_count={len(slots)}")

    # Extract any time preference from the conversation so far
    pref = extract_time_preference_from_conversation(conv)
    plog.info(
        f"{log_prefix} pref.has_preference={pref.has_preference} "
        f"date='{pref.requested_date}' time='{pref.requested_time}'",
        is_pii=True,
    )

    no_pref_match = False
    if pref.has_preference:
        offered = select_closest_slot(
            requested_date=pref.requested_date,
            requested_time=pref.requested_time,
            slots=slots,
        )
        if offered is None:
            offered = get_next_available_slot(slots)
            no_pref_match = True
            plog.info(f"{log_prefix} no pref match; falling back to next available")
    else:
        offered = get_next_available_slot(slots)
        plog.info(f"{log_prefix} no preference stated; offering next available")

    if offered is None:
        plog.info(f"{log_prefix} no slots found at all; exiting")
        conv.exit_flow()
        return {
            "utterance": (
                "I'm not finding any available times in the next 90 days. "
                "Let me transfer you to someone who can help."
            )
        }

    # Resolve provider name from real_time_config for the offered slot
    _slot_resource_id = offered.resource_id or (
        offered.resource_ids[0] if offered.resource_ids else None
    )
    # Inline provider name lookup from prefetched_resources state
    _provider_name = None
    if _slot_resource_id:
        for _r in getattr(conv.state, "prefetched_resources", None) or []:
            if isinstance(_r, dict) and _r.get("resource_id") == _slot_resource_id:
                _provider_name = _r.get("resource_display_name")
                break
    plog.info(
        f"{log_prefix} slot_resource_id='{_slot_resource_id}' provider_name='{_provider_name}'",
        is_pii=True,
    )

    conv.state.reschedule_offered_slot = offered.model_dump(mode="json")
    conv.state.reschedule_declined_slot_starts = []
    conv.state.reschedule_offered_slot_display = format_slot_display(
        offered, provider_name=_provider_name
    )
    plog.info(
        f"{log_prefix} offered_slot_start='{offered.start_date}' "
        f"display='{conv.state.reschedule_offered_slot_display}'",
        is_pii=True,
    )
    conv.write_metric("RESCHEDULE_FLOW_SLOT_OFFERED")

    flow.goto_step("Offer Slot")

    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    neighborhood_fallback = getattr(conv.state, "reschedule_neighborhood_fallback", False)
    nbr_utterance = (
        (
            "The patient's primary provider doesn't have any openings right now, but I do have some times available with another provider on their care team. "
            if is_cm
            else "Your primary provider doesn't have any openings right now, but I do have some times available with another provider on your care team. "
        )
        if neighborhood_fallback
        else ""
    )
    display = conv.state.reschedule_offered_slot_display
    does_that_work = "Does that work?" if is_cm else "Does that work for you?"

    if no_pref_match:
        return {
            "utterance": f"{nbr_utterance}I wasn't able to find anything that matches {'their' if is_cm else 'your'} preference, but the next available time is {display}. {does_that_work}",
        }
    return {
        "utterance": f"{nbr_utterance}I have an opening on {display}. {does_that_work}",
    }
