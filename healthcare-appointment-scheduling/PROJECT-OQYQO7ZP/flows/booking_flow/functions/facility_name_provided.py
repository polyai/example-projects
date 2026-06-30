"""Called when the caller provides the facility name; fetches slots filtered to the discharge window."""

from datetime import UTC, datetime, timedelta

import plog
from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import get_blocked_booking_dates
from functions.extract_time_preference import extract_time_preference_from_conversation
from functions.fetch_available_slots import (
    _FOLLOW_UP_CATEGORY_ID,
    FPIM_SD_CATEGORY_ID,
    _apply_booking_filters,
    _fetch_neighborhood_slots,
    fetch_booking_slots_for_state,
    filter_slots_for_extended_appointment,
)
from functions.get_grace_nextgen_api_handler import get_grace_nextgen_api_handler
from functions.handoff import handoff
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import (
    format_slot_offer_display,
    get_top_n_available_slots,
    get_top_n_preference_slots,
)

_DISCHARGE_WINDOW_DAYS = {
    "hospital_follow_up": 7,
    "er_follow_up": 14,
}


@func_description(
    "Called when the caller provides the name of the hospital or ER. Fetches available slots, filters them to the discharge window, and offers the best options."
)
@func_parameter(
    "facility_name",
    "The name of the hospital or ER as stated by the caller. Use 'unknown' if the caller doesn't know.",
)
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=3,
    delay_responses=[("typing_noise_long", 3), ("typing_noise_short", 2)],
)
def facility_name_provided(conv: Conversation, flow: Flow, facility_name: str):
    """Store facility name, filter slots to discharge window, and offer the best two."""
    log_prefix = "[facility_name_provided.facility_name_provided]: "
    appt_type = conv.state.booking_appointment_type
    discharge_date_str = conv.state.booking_discharge_date
    plog.info(
        f"{log_prefix} facility_name='{facility_name}' appt_type='{appt_type}' "
        f"discharge_date='{discharge_date_str}'",
        is_pii=True,
    )

    # Guard: prevent infinite loop when facility_name is "unknown"
    if facility_name.strip().lower() == "unknown":
        unknown_attempts = getattr(conv.state, "booking_facility_name_unknown_attempts", 0) or 0
        unknown_attempts += 1
        conv.state.booking_facility_name_unknown_attempts = unknown_attempts
        plog.info(f"{log_prefix} unknown facility attempt #{unknown_attempts}")
        if unknown_attempts >= 2:
            plog.info(f"{log_prefix} repeated unknown facility; handing off")
            conv.write_metric("BOOKING_FLOW_FACILITY_NAME", "unknown")
            return handoff(
                conv,
                reason="BOOKING_FACILITY_NAME_UNAVAILABLE",
                utterance="No problem. Let me transfer you to someone who can help look that up.",
            )

    conv.state.booking_facility_name = facility_name
    conv.write_metric("BOOKING_FLOW_FACILITY_NAME", facility_name)

    # Build details string for the chart
    type_label = "Hospital follow-up" if appt_type == "hospital_follow_up" else "ER follow-up"
    details = f"{type_label} - seen at {facility_name}, discharged {discharge_date_str}"
    conv.state.booking_appointment_details = details
    plog.info(f"{log_prefix} details='{details}'", is_pii=True)

    # Fetch available slots into state
    fetch_result = fetch_booking_slots_for_state(conv)
    if not fetch_result.ok:
        plog.info(f"{log_prefix} slot fetch failed; handing off")
        return handoff(
            conv,
            reason="BOOKING_NO_SLOTS_AVAILABLE",
            utterance="I'm not able to look up available times right now. Let me transfer you to someone who can help.",
        )

    # Parse discharge date and compute cutoff
    window_days = _DISCHARGE_WINDOW_DAYS.get(appt_type, 14)
    try:
        discharge_date = datetime.strptime(discharge_date_str, "%Y-%m-%d").date()
        cutoff_date = discharge_date + timedelta(days=window_days)
    except (ValueError, TypeError) as e:
        plog.info(f"{log_prefix} discharge_date parse failed error='{e}'; handing off", is_pii=True)
        conv.log.error(
            "facility_name_provided: could not parse discharge date",
            discharge_date=discharge_date_str,
            error=str(e),
            is_pii=True,
        )
        return handoff(
            conv,
            reason="BOOKING_DISCHARGE_DATE_PARSE_ERROR",
            utterance="We ran into an issue with that date. Let me transfer you to someone who can help.",
        )

    plog.info(f"{log_prefix} window_days={window_days} cutoff_date='{cutoff_date}'", is_pii=True)

    # Persist discharge-window constraints so any later neighborhood fallback reuses
    # the same effective booking search window.
    conv.state.booking_slot_search_end_iso = cutoff_date.strftime("%Y-%m-%dT23:59:59")

    # Filter slots to within the discharge window
    raw_slots = getattr(conv.state, "booking_available_slots", None) or []
    all_slots = [AppointmentSlot.model_validate(s) for s in raw_slots]
    windowed_slots = _filter_slots_by_cutoff(all_slots, cutoff_date)
    plog.info(
        f"{log_prefix} total_slots={len(all_slots)} windowed_slot_count={len(windowed_slots)}"
    )

    if not windowed_slots:
        nbr_already_tried = bool(getattr(conv.state, "booking_neighborhood_fallback", False))
        if not nbr_already_tried:
            plog.info(
                f"{log_prefix} no slots in discharge window with primary category; "
                "trying neighborhood providers with follow-up category before FP/IM SD (same day) fallback"
            )
            resource_id = getattr(conv.state, "patient_resource_id", None) or None
            now = datetime.now(UTC)
            start_iso = getattr(conv.state, "booking_slot_search_start_iso", None) or now.strftime(
                "%Y-%m-%dT00:00:00"
            )
            end_iso = (now + timedelta(days=90)).strftime("%Y-%m-%dT23:59:59")
            try:
                handler = get_grace_nextgen_api_handler(conv)
                nbr_raw = _fetch_neighborhood_slots(
                    conv,
                    handler,
                    resource_id,
                    start_iso,
                    end_iso,
                    _FOLLOW_UP_CATEGORY_ID,
                )
                language_barrier = bool(getattr(conv.state, "patient_language_barrier", False))
                blocked_dates = get_blocked_booking_dates(conv, start_iso, end_iso)
                nbr_slots = _apply_booking_filters(nbr_raw, now, language_barrier, blocked_dates)
                windowed_nbr = _filter_slots_by_cutoff(nbr_slots, cutoff_date)
                if windowed_nbr:
                    conv.state.booking_neighborhood_fallback = True
                    windowed_slots = windowed_nbr
                    conv.state.booking_slot_search_category_id = _FOLLOW_UP_CATEGORY_ID
                    conv.state.booking_slot_search_start_iso = start_iso
                    conv.state.booking_slot_search_end_iso = cutoff_date.strftime(
                        "%Y-%m-%dT23:59:59"
                    )
                    plog.info(
                        f"{log_prefix} neighborhood follow-up: "
                        f"filtered={len(nbr_slots)} windowed={len(windowed_slots)}"
                    )
            except Exception as e:
                plog.info(f"{log_prefix} neighborhood follow-up fetch failed: {e}")
                conv.log.error(
                    "facility_name_provided: neighborhood follow-up fetch failed",
                    error=str(e),
                    resource_id=resource_id,
                    start_iso=start_iso,
                    end_iso=end_iso,
                    category_id=_FOLLOW_UP_CATEGORY_ID,
                )
                conv.write_metric("BOOKING_FLOW_NEIGHBORHOOD_FETCH_FAILED")

        if not windowed_slots:
            plog.info(
                f"{log_prefix} no slots in discharge window with primary category; "
                f"retrying with fallback category '{FPIM_SD_CATEGORY_ID}'"
            )
            fallback_result = fetch_booking_slots_for_state(
                conv, category_id_override=FPIM_SD_CATEGORY_ID
            )
            if fallback_result.ok:
                # Re-apply discharge-window bounds because fetch_booking_slots_for_state persists
                # its own defaults/overrides to state, which may not include the discharge cutoff.
                conv.state.booking_slot_search_end_iso = cutoff_date.strftime("%Y-%m-%dT23:59:59")

                # Ensure downstream neighborhood fallback uses the same effective category.
                conv.state.booking_slot_search_category_id = FPIM_SD_CATEGORY_ID
                fb_raw = getattr(conv.state, "booking_available_slots", None) or []
                fb_slots = [AppointmentSlot.model_validate(s) for s in fb_raw]
                windowed_slots = _filter_slots_by_cutoff(fb_slots, cutoff_date)
                plog.info(
                    f"{log_prefix} fallback category: "
                    f"total={len(fb_slots)} windowed={len(windowed_slots)}"
                )

    if not windowed_slots:
        plog.info(f"{log_prefix} no slots within discharge window; handing off")
        conv.write_metric("BOOKING_FLOW_NO_SLOTS_IN_DISCHARGE_WINDOW")
        is_cm = getattr(conv.state, "caller_is_case_manager", False)
        no_slots_utterance = (
            f"I'm not seeing any available appointments within {window_days} days of the patient's discharge. Let me transfer you to someone who can help."
            if is_cm
            else f"I'm not seeing any available appointments within {window_days} days of your discharge. Let me transfer you to someone who can help."
        )
        return handoff(
            conv,
            reason="BOOKING_NO_SLOTS_IN_DISCHARGE_WINDOW",
            utterance=no_slots_utterance,
        )

    # Apply extended appointment filter (:00/:45 only) if the patient has an extended alert
    if getattr(conv.state, "patient_needs_extended_appointment", False):
        pre_ext = len(windowed_slots)
        windowed_slots = filter_slots_for_extended_appointment(windowed_slots)
        plog.info(
            f"{log_prefix} extended appointment: filtered {pre_ext} -> {len(windowed_slots)} slots"
        )
        if not windowed_slots:
            plog.info(f"{log_prefix} no :00/:45 slots for extended appointment; handing off")
            return handoff(
                conv,
                reason="BOOKING_NO_EXTENDED_SLOTS",
                utterance=(
                    "I'm not finding any available appointment times that fit the extended "
                    "scheduling requirement. Let me transfer you to someone who can help."
                ),
            )

    # Overwrite state with filtered slots so downstream functions only see window-valid slots
    conv.state.booking_available_slots = [s.model_dump(mode="json") for s in windowed_slots]

    # Offer best 2 slots, respecting any stated preference
    pref = extract_time_preference_from_conversation(conv)
    plog.info(
        f"{log_prefix} pref.has_preference={pref.has_preference} "
        f"date='{pref.requested_date}' time='{pref.requested_time}'",
        is_pii=True,
    )

    no_pref_match = False
    offered: list[AppointmentSlot] = []

    if pref.has_preference:
        offered = get_top_n_preference_slots(
            requested_date=pref.requested_date,
            requested_time=pref.requested_time,
            slots=windowed_slots,
            n=2,
        )
        if not offered:
            no_pref_match = True
            offered = get_top_n_available_slots(windowed_slots, n=2)
            conv.state.booking_no_pref_match_confirmed = True
            plog.info(f"{log_prefix} no pref match; falling back to two earliest")
        else:
            plog.info(f"{log_prefix} preference matched {len(offered)} slot(s)")
    else:
        offered = get_top_n_available_slots(windowed_slots, n=2)
        plog.info(f"{log_prefix} no preference; offering two earliest slots")

    conv.state.booking_offered_slot_1 = offered[0].model_dump(mode="json")
    conv.state.booking_offered_slot_2 = (
        offered[1].model_dump(mode="json") if len(offered) > 1 else None
    )
    conv.state.booking_offered_slot_3 = None

    slots_display = format_slot_offer_display(offered)
    conv.state.booking_offered_slots_display = slots_display
    conv.write_metric("BOOKING_FLOW_SLOTS_OFFERED")

    plog.info(
        f"{log_prefix} offering display='{slots_display[:80]}' no_pref_match={no_pref_match}",
        is_pii=True,
    )

    flow.goto_step("Offer Booking Slot")

    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    nbr = getattr(conv.state, "booking_neighborhood_fallback", False)
    nbr_utterance = (
        (
            "The patient's primary provider doesn't have any openings right now, but I do have some times available with another provider on their care team. "
            if is_cm
            else "Your primary provider doesn't have any openings right now, but I do have some times available with another provider on your care team. "
        )
        if nbr
        else ""
    )
    work_for = "Would one of those work?" if is_cm else "Would one of those work for you?"

    if no_pref_match:
        return {
            "utterance": f"{nbr_utterance}I wasn't able to find anything at that time, but I'm seeing {slots_display}. {work_for}",
        }
    return {
        "utterance": f"{nbr_utterance}Alright, I'm seeing {slots_display}. {work_for}",
    }


def _filter_slots_by_cutoff(slots: list[AppointmentSlot], cutoff_date) -> list[AppointmentSlot]:
    """Return only slots whose start date falls on or before cutoff_date."""
    result = []
    for slot in slots:
        if not slot.start_date:
            continue
        try:
            slot_date = datetime.strptime(str(slot.start_date)[:10], "%Y-%m-%d").date()
            if slot_date <= cutoff_date:
                result.append(slot)
        except ValueError:
            continue
    return result
