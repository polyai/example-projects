"""Called when the caller provides their discharge date during the reschedule flow for hospital/ER follow-ups."""

from datetime import datetime, timedelta
from typing import Any

import plog
from _gen import *  # <AUTO GENERATED>
from functions.extract_time_preference import extract_time_preference_from_conversation
from functions.fetch_available_slots import fetch_available_slots_for_state
from functions.handoff import handoff
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import (
    format_slot_display,
    get_next_available_slot,
    select_closest_slot,
)

_DISCHARGE_WINDOW_DAYS = {
    "hospital_follow_up": 7,
    "er_follow_up": 14,
}


@func_description(
    "Called when the caller provides their discharge date while rescheduling a hospital or ER follow-up. Validates the discharge window and fetches available slots."
)
@func_parameter(
    "discharge_date", "The caller's discharge date in YYYY-MM-DD format (e.g. '2026-03-25')."
)
def reschedule_discharge_date_provided(
    conv: Conversation, flow: Flow, discharge_date: str
) -> dict[str, Any]:
    """Validate discharge window, fetch constrained slots, and offer the best one."""
    log_prefix = "[reschedule_discharge_date_provided.reschedule_discharge_date_provided]: "
    plog.info(f"{log_prefix} discharge_date='{discharge_date}'", is_pii=True)

    conv.state.reschedule_discharge_date = discharge_date
    conv.write_metric("RESCHEDULE_FLOW_DISCHARGE_DATE", discharge_date)

    # Check if the discharge window has already expired
    appt_type = getattr(conv.state, "reschedule_target_appointment_type", None) or ""
    window_days = _DISCHARGE_WINDOW_DAYS.get(appt_type, 14)
    try:
        parsed_date = datetime.strptime(discharge_date, "%Y-%m-%d").date()
        cutoff_date = parsed_date + timedelta(days=window_days)
        today = datetime.now().date()
        plog.info(
            f"{log_prefix} window_days={window_days} cutoff_date='{cutoff_date}' today='{today}'",
            is_pii=True,
        )
        if today > cutoff_date:
            plog.info(f"{log_prefix} discharge window has passed; handing off")
            conv.write_metric("RESCHEDULE_FLOW_DISCHARGE_WINDOW_EXPIRED")
            is_cm = getattr(conv.state, "caller_is_case_manager", False)
            expired_utterance = (
                f"It sounds like the patient's discharge was more than {window_days} days ago. "
                "I'll need to transfer you to someone who can help get that appointment set up."
                if is_cm
                else f"It sounds like your discharge was more than {window_days} days ago. I'll need to transfer you to someone who can help get that appointment set up."
            )
            return handoff(
                conv,
                reason="RESCHEDULE_DISCHARGE_WINDOW_EXPIRED",
                utterance=expired_utterance,
            )
    except (ValueError, TypeError) as e:
        plog.info(f"{log_prefix} could not parse discharge_date for window check: {e}", is_pii=True)

    # Constrain slot search to the discharge window
    start_iso = f"{discharge_date}T00:00:00"
    end_date = parsed_date + timedelta(days=window_days)
    end_iso = f"{end_date.isoformat()}T23:59:59"
    plog.info(f"{log_prefix} slot window: start='{start_iso}' end='{end_iso}'", is_pii=True)

    # Fetch available slots within the discharge window
    preload = fetch_available_slots_for_state(conv, start_override=start_iso, end_override=end_iso)
    if not preload.ok:
        plog.info(f"{log_prefix} slot fetch failed or no slots in window")
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
        plog.info(f"{log_prefix} no slots found; exiting")
        facility_label = getattr(conv.state, "reschedule_facility_type_label", "facility")
        is_cm = getattr(conv.state, "caller_is_case_manager", False)
        conv.exit_flow()
        return {
            "utterance": (
                f"I'm not finding any available times within {window_days} days of the patient's "
                f"{facility_label} discharge. Let me transfer you to someone who can help."
                if is_cm
                else f"I'm not finding any available times within {window_days} days of your "
                f"{facility_label} discharge. Let me transfer you to someone who can help."
            )
        }

    # Resolve provider name for the offered slot
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
