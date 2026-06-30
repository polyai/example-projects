"""Called when the caller confirms an eligible appointment type; fetches slots and offers the first two."""

from datetime import UTC, datetime, timedelta

import plog
from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import get_recall_window, is_recheck_type
from functions.extract_time_preference import extract_time_preference_from_conversation
from functions.fetch_available_slots import (
    FPIM_SD_CATEGORY_ID,
    fetch_booking_slots_for_state,
    filter_slots_for_extended_appointment,
)
from functions.handoff import handoff
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import (
    format_slot_offer_display,
    get_top_n_available_slots,
    get_top_n_preference_slots,
)


def _is_today_request(requested_date: str | None, today_iso: str) -> bool:
    """Return True if the requested_date resolves to today (handles both 'today' and ISO dates)."""
    if not requested_date:
        return False
    rd = requested_date.strip().lower()
    return rd == "today" or rd.startswith(today_iso)


@func_description(
    "Called when the caller confirms they want to book an eligible appointment type. Fetches available slots and offers the best two options."
)
@func_parameter(
    "appointment_type",
    "The type of appointment to book: 'recheck', 'recheck_diabetes', 'recheck_hypertension', 'recheck_medication', 'ill', 'hospital_follow_up', or 'er_follow_up'.",
)
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=3,
    delay_responses=[("typing_noise_short", 2), ("typing_noise_long", 4)],
)
def appointment_type_confirmed(conv: Conversation, flow: Flow, appointment_type: str):
    """Route hospital/ER types to overnight-stay collection; fetch slots for recheck/ill."""
    log_prefix = "[appointment_type_confirmed.appointment_type_confirmed]: "
    plog.info(f"{log_prefix} appointment_type='{appointment_type}'")

    conv.state.booking_appointment_type = appointment_type
    conv.write_metric("BOOKING_FLOW_TYPE_CONFIRMED", appointment_type)

    _APPOINTMENT_TYPE_LABELS = {
        "recheck": "Recheck follow-up",
        "recheck_diabetes": "Diabetes recheck",
        "recheck_hypertension": "Hypertension recheck",
        "recheck_medication": "Medication recheck",
        "ill": "New concern",
        "hospital_follow_up": "Hospital follow-up",
        "er_follow_up": "ER follow-up",
    }
    if not getattr(conv.state, "booking_appointment_details", None):
        conv.state.booking_appointment_details = _APPOINTMENT_TYPE_LABELS.get(
            appointment_type, appointment_type
        )

    # Hospital and ER follow-ups require admission clarification before slot fetching
    if appointment_type == "hospital_follow_up":
        conv.state.booking_facility_type_label = "hospital"
        flow.goto_step("Collect Admission Type")
        if getattr(conv.state, "caller_is_case_manager", False):
            return {
                "utterance": "Was the patient admitted into the hospital, or did they stay in the ER?"
            }
        return {"utterance": ("Were you admitted into the hospital, or did you stay in the ER?")}

    if appointment_type == "er_follow_up":
        conv.state.booking_facility_type_label = "emergency room"
        flow.goto_step("Collect Admission Type")
        if getattr(conv.state, "caller_is_case_manager", False):
            return {
                "utterance": "Was the patient admitted into the hospital, or did they stay in the ER?"
            }
        return {"utterance": ("Were you admitted into the hospital, or did you stay in the ER?")}

    # Check if patient has a cell phone on file — required for booking
    identified = getattr(conv.state, "identified_patient", None)
    cell_phone = identified.get("cellPhone") if isinstance(identified, dict) else None
    if not cell_phone:
        plog.info(f"{log_prefix} no cellPhone on patient record; routing to Collect Cell Phone")
        flow.goto_step("Collect Cell Phone")
        return {
            "utterance": (
                "Before I can complete your booking, I need a cell phone number on file — "
                "our scheduling system requires it. Could you provide your cell phone number?"
            )
        }

    # Recheck types use recall-plan windowing around expectedReturnDate
    start_override = None
    end_override = None
    category_override = None

    if is_recheck_type(appointment_type):
        recall = get_recall_window(conv, appointment_type)
        if recall.needs_disambiguation:
            options = recall.disambiguation_options or []
            conv.state.booking_recheck_disambiguation = options
            plog.info(
                f"{log_prefix} recheck disambiguation needed; routing to Collect Recheck Type"
            )
            flow.goto_step("Collect Recheck Type")
            labels = [opt.get("description", opt["appointment_type"]) for opt in options]
            options_text = (
                ", ".join(labels[:-1]) + f", or {labels[-1]}"
                if len(labels) > 2
                else " or ".join(labels)
            )
            return {
                "utterance": f"I can see a few different recheck types on file. Is this for your {options_text} follow-up?"
            }
        if not recall.ok:
            plog.info(f"{log_prefix} no recall found for '{appointment_type}'; offering new visit")
            conv.write_metric("BOOKING_NO_RECALL_FOUND")
            flow.goto_step("Confirm No Recall Fallback")
            if appointment_type == "recheck":
                return {
                    "utterance": (
                        "I don't see a recall record on file for a follow-up. "
                        "Would you like to schedule a visit to discuss your concern "
                        "with your provider instead?"
                    )
                }
            return {
                "utterance": (
                    "I don't see a recall record on file for that type of recheck. "
                    "Would you like to schedule a visit to discuss your concern "
                    "with your provider instead?"
                )
            }
        if recall.resolved_appointment_type:
            appointment_type = recall.resolved_appointment_type
            conv.state.booking_appointment_type = appointment_type
            conv.write_metric("BOOKING_FLOW_TYPE_CONFIRMED", appointment_type)
            plog.info(f"{log_prefix} refined appointment_type to '{appointment_type}' from recall")
        start_override = recall.start_iso
        end_override = recall.end_iso
        conv.state.booking_recall_expected_return_date = recall.expected_return_date

    if appointment_type == "ill":
        now = datetime.now(UTC)
        today_start = now.strftime("%Y-%m-%dT00:00:00")
        today_end = now.strftime("%Y-%m-%dT23:59:59")
        plog.info(f"{log_prefix} ill visit: trying FP/IM SD same-day slots first")
        sd_result = fetch_booking_slots_for_state(
            conv,
            start_override=today_start,
            end_override=today_end,
            category_id_override=FPIM_SD_CATEGORY_ID,
            skip_blocked_dates=True,
        )
        sd_slots = getattr(conv.state, "booking_available_slots", None) or []
        if sd_result.ok and sd_slots:
            plog.info(f"{log_prefix} ill visit: found {len(sd_slots)} FP/IM SD same-day slot(s)")
            conv.state.booking_used_same_day_category = True
        else:
            plog.info(f"{log_prefix} ill visit: no FP/IM SD same-day slots; falling back to FP/IM")

    # Fetch available slots into state (skipped for ill visits that already found SD slots)
    already_fetched = appointment_type == "ill" and getattr(
        conv.state, "booking_used_same_day_category", False
    )
    if not already_fetched:
        fetch_result = fetch_booking_slots_for_state(
            conv,
            start_override=start_override,
            end_override=end_override,
            category_id_override=category_override,
        )
        if not fetch_result.ok:
            plog.info(f"{log_prefix} slot fetch failed; handing off")
            return handoff(
                conv,
                reason="BOOKING_NO_SLOTS_AVAILABLE",
                utterance="I'm not able to look up available times right now. Let me transfer you to someone who can help.",
            )

    raw_slots = getattr(conv.state, "booking_available_slots", None) or []
    all_slots = [AppointmentSlot.model_validate(s) for s in raw_slots]

    if getattr(conv.state, "patient_needs_extended_appointment", False):
        pre_count = len(all_slots)
        all_slots = filter_slots_for_extended_appointment(all_slots)
        plog.info(
            f"{log_prefix} extended appointment: filtered {pre_count} -> {len(all_slots)} slots"
        )
        if not all_slots:
            plog.info(f"{log_prefix} no :00/:45 slots for extended appointment; handing off")
            return handoff(
                conv,
                reason="BOOKING_NO_EXTENDED_SLOTS",
                utterance=(
                    "I'm not finding any available appointment times that fit the extended "
                    "scheduling requirement. Let me transfer you to someone who can help."
                ),
            )

    # Check conversation history for any stated scheduling preference
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
            slots=all_slots,
            n=2,
        )
        if not offered:
            no_pref_match = True
            offered = get_top_n_available_slots(all_slots, n=2)
            plog.info(f"{log_prefix} no pref match; falling back to two earliest")
            conv.state.booking_no_pref_match_confirmed = True
        else:
            plog.info(f"{log_prefix} preference matched {len(offered)} slot(s)")
    else:
        offered = get_top_n_available_slots(all_slots, n=2)
        plog.info(f"{log_prefix} no preference stated; offering two earliest slots")

    if not offered:
        plog.info(f"{log_prefix} no slots available; handing off")
        return handoff(
            conv,
            reason="BOOKING_NO_SLOTS_AVAILABLE",
            utterance="I'm not seeing any available appointment times in the next 90 days. Let me transfer you to someone who can help.",
        )

    # Store offered slots in state (up to 2 for the initial offer)
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

    nbr = getattr(conv.state, "booking_neighborhood_fallback", False)
    nbr_utterance = (
        "Your primary provider doesn't have any openings right now, but I do have some times available with another provider on your care team. "
        if nbr
        else ""
    )

    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    requested_today = _is_today_request(pref.requested_date, today_str)
    offered_has_today = any(str(s.start_date or "").startswith(today_str) for s in offered)

    if requested_today and not offered_has_today and appointment_type == "ill":
        plog.info(f"{log_prefix} ill visit requested today but no today slots; confirming need")
        flow.goto_step("Confirm Same Day Need")
        return {
            "utterance": (
                "I'm not seeing any openings for today. Do you need to be seen today "
                "specifically, or would another day work as well?"
            )
        }

    if no_pref_match or (requested_today and not offered_has_today):
        if requested_today and not offered_has_today:
            no_match_msg = "I wasn't able to find any appointments for today, but the next available times I'm seeing are"
        else:
            no_match_msg = "I wasn't able to find anything at that time, but I'm seeing"
        return {
            "utterance": (
                f"{nbr_utterance}{no_match_msg} {slots_display}. Would one of those work for you?"
            )
        }
    return {
        "utterance": f"{nbr_utterance}Alright, I'm seeing {slots_display}. Would one of those work for you?"
    }


def _handle_diabetes_recheck(conv: Conversation, flow: Flow):
    """Fetch slots for a diabetes recheck booking, constrained to the 83–91 day follow-up window."""
    log_prefix = "[appointment_type_confirmed._handle_diabetes_recheck]: "

    # Cell-phone check (same gate as other types)
    identified = getattr(conv.state, "identified_patient", None)
    cell_phone = identified.get("cellPhone") if isinstance(identified, dict) else None
    if not cell_phone:
        plog.info(f"{log_prefix} no cellPhone; routing to Collect Cell Phone")
        flow.goto_step("Collect Cell Phone")
        return {
            "utterance": (
                "Before I can complete your booking, I need a cell phone number on file — "
                "our scheduling system requires it. Could you provide your cell phone number?"
            )
        }

    # Look up last completed diabetes recheck visit to compute the scheduling window
    person_id = identified.get("id") if isinstance(identified, dict) else None
    window_start_iso = None
    window_end_iso = None

    if person_id:
        try:
            handler = get_grace_nextgen_api_handler(conv)
            past_appts = handler.get_person_appointments(person_id, fetch_all_pages=True)
            recheck_appts = [
                a
                for a in past_appts
                if a.event_id == _RECHECK_DIABETES_EVENT_ID and not a.is_cancelled and a.is_kept
            ]
            if recheck_appts:
                recheck_appts.sort(key=lambda a: a.appointment_date or "", reverse=True)
                last_date_str = (recheck_appts[0].appointment_date or "")[:10]
                last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
                window_start = last_date + timedelta(days=_DIABETES_WINDOW_MIN_DAYS)
                window_end = last_date + timedelta(days=_DIABETES_WINDOW_MAX_DAYS)
                window_start_iso = window_start.strftime("%Y-%m-%dT00:00:00")
                window_end_iso = window_end.strftime("%Y-%m-%dT23:59:59")
                plog.info(
                    f"{log_prefix} last_recheck='{last_date_str}' "
                    f"window=['{window_start_iso}', '{window_end_iso}']",
                    is_pii=True,
                )
            else:
                plog.info(
                    f"{log_prefix} no prior diabetes recheck found; using standard 90-day window"
                )
        except Exception as e:
            conv.log.error("diabetes recheck history lookup failed", error=str(e))
            plog.info(
                f"{log_prefix} appointment history lookup failed; using standard 90-day window"
            )
    else:
        plog.info(f"{log_prefix} no person_id on identified_patient; using standard 90-day window")

    # Fetch slots within the computed window (neighborhood fallback handled inside)
    fetch_result = fetch_booking_slots_for_state(
        conv, start_override=window_start_iso, end_override=window_end_iso
    )
    if not fetch_result.ok:
        plog.info(f"{log_prefix} slot fetch failed; handing off")
        return handoff(
            conv,
            reason="BOOKING_NO_SLOTS_AVAILABLE",
            utterance="I'm not seeing available appointments right now. Let me transfer you to someone who can help.",
        )

    raw_slots = getattr(conv.state, "booking_available_slots", None) or []
    all_slots = [AppointmentSlot.model_validate(s) for s in raw_slots]

    if not all_slots:
        plog.info(f"{log_prefix} no slots in diabetes window; handing off")
        conv.write_metric("BOOKING_NO_SLOTS_IN_DIABETES_WINDOW")
        return handoff(
            conv,
            reason="BOOKING_NO_SLOTS_IN_DIABETES_WINDOW",
            utterance=(
                "I'm not seeing any available appointment times within the required scheduling window. "
                "Let me transfer you to someone who can help find a time."
            ),
        )

    pref = extract_time_preference_from_conversation(conv)
    plog.info(
        f"{log_prefix} pref.has_preference={pref.has_preference} "
        f"date='{pref.requested_date}' time='{pref.requested_time}'",
        is_pii=True,
    )

    offered: list[AppointmentSlot] = []
    no_pref_match = False

    if pref.has_preference:
        offered = get_top_n_preference_slots(
            requested_date=pref.requested_date,
            requested_time=pref.requested_time,
            slots=all_slots,
            n=2,
        )
        if not offered:
            no_pref_match = True
            offered = get_top_n_available_slots(all_slots, n=2)
            conv.state.booking_no_pref_match_confirmed = True
            plog.info(f"{log_prefix} no pref match; falling back to two earliest")
        else:
            plog.info(f"{log_prefix} preference matched {len(offered)} slot(s)")
    else:
        offered = get_top_n_available_slots(all_slots, n=2)
        plog.info(f"{log_prefix} no preference stated; offering two earliest slots")

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

    nbr = getattr(conv.state, "booking_neighborhood_fallback", False)
    nbr_utterance = (
        "Your primary provider doesn't have any openings right now, but I do have some times available with another provider on your care team. "
        if nbr
        else ""
    )

    if no_pref_match:
        return {
            "utterance": (
                f"{nbr_utterance}I wasn't able to find anything at that time, but I'm seeing "
                f"{slots_display}. Would one of those work for you?"
            )
        }
    return {
        "utterance": f"{nbr_utterance}Alright, I'm seeing {slots_display}. Would one of those work for you?"
    }
