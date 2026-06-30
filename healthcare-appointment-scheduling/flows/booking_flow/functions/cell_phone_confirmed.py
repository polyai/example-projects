"""Called when the caller confirms their cell phone number; PATCHes the patient record, then fetches slots."""

import plog
from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import get_recall_window, is_recheck_type
from functions.extract_time_preference import extract_time_preference_from_conversation
from functions.fetch_available_slots import fetch_booking_slots_for_state
from functions.get_grace_nextgen_api_handler import get_grace_nextgen_api_handler
from functions.handoff import handoff
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import (
    format_slot_offer_display,
    get_top_n_available_slots,
    get_top_n_preference_slots,
)


@func_description(
    "Called when the caller confirms their cell phone number is correct. Saves the number to their patient record, then fetches available appointment slots."
)
def cell_phone_confirmed(conv: Conversation, flow: Flow):
    log_prefix = "[cell_phone_confirmed.cell_phone_confirmed]: "

    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    phone_error_utterance = (
        "We ran into an issue saving the patient's phone number. Let me transfer you to someone who can help."
        if is_cm
        else "We ran into an issue saving your phone number. Let me transfer you to someone who can help."
    )

    cell_phone = getattr(conv.state, "booking_cell_phone", None)
    if not cell_phone:
        plog.info(f"{log_prefix} no booking_cell_phone in state; handing off")
        conv.log.error("cell_phone_confirmed: no cell phone in state")
        return handoff(
            conv,
            reason="BOOKING_CELL_PHONE_MISSING",
            utterance=phone_error_utterance,
        )

    identified = getattr(conv.state, "identified_patient", None)
    person_id = identified.get("id") if isinstance(identified, dict) else None
    if not person_id:
        plog.info(f"{log_prefix} no identified_patient or missing id; handing off")
        conv.log.error("cell_phone_confirmed: no patient id on state")
        return handoff(
            conv,
            reason="BOOKING_NO_PATIENT_ID",
            utterance=phone_error_utterance,
        )

    cell_phone_saved = False
    try:
        handler = get_grace_nextgen_api_handler(conv)
        handler.update_person_cell_phone(person_id, cell_phone)
        plog.info(f"{log_prefix} cell phone updated for person_id last4='{str(person_id)[-4:]}'")
        cell_phone_saved = True
    except Exception as e:
        plog.info(
            f"{log_prefix} update_person_cell_phone failed error='{e}'; continuing with booking"
        )
        conv.log.error("cell_phone_confirmed: PATCH cell phone failed", error=str(e))

    # Update identified_patient in state with new cellPhone regardless (so we don't re-ask)
    if isinstance(identified, dict):
        identified["cellPhone"] = cell_phone
        conv.state.identified_patient = identified

    if cell_phone_saved:
        conv.write_metric("BOOKING_FLOW_CELL_PHONE_UPDATED")

    # Recheck types use recall-plan windowing around expectedReturnDate
    appointment_type = getattr(conv.state, "booking_appointment_type", None)
    start_override = None
    end_override = None

    if is_recheck_type(appointment_type or ""):
        recall = get_recall_window(conv, appointment_type)
        if not recall.ok:
            # TODO: Waiting on Poly Clinic for the ideal handling when no recall
            # record exists. For now, hand off so a human scheduler can assist.
            plog.info(f"{log_prefix} no recall found for '{appointment_type}'; handing off")
            conv.write_metric("BOOKING_NO_RECALL_FOUND")
            return handoff(
                conv,
                reason="BOOKING_NO_RECALL",
                utterance=(
                    "I wasn't able to find a recall record for that type of recheck. "
                    "Let me transfer you to someone who can help schedule that."
                ),
            )
        start_override = recall.start_iso
        end_override = recall.end_iso
        conv.state.booking_recall_expected_return_date = recall.expected_return_date

    # Fetch available slots into state
    fetch_result = fetch_booking_slots_for_state(
        conv, start_override=start_override, end_override=end_override
    )
    if not fetch_result.ok:
        plog.info(f"{log_prefix} slot fetch failed; handing off")
        phone_updated_utterance = (
            "I've updated the patient's cell phone number. However, I'm not able to look up available times right now. Let me transfer you to someone who can help."
            if is_cm
            else "I've updated your cell phone number. However, I'm not able to look up available times right now. Let me transfer you to someone who can help."
        )
        return handoff(
            conv,
            reason="BOOKING_NO_SLOTS_AVAILABLE",
            utterance=phone_updated_utterance,
        )

    raw_slots = getattr(conv.state, "booking_available_slots", None) or []
    all_slots = [AppointmentSlot.model_validate(s) for s in raw_slots]

    # For diabetes recheck: if nothing in window even after neighborhood fallback, hand off
    if appointment_type == "recheck_diabetes" and not all_slots:
        plog.info(f"{log_prefix} recheck_diabetes: no slots in window; handing off")
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

    conv.state.booking_offered_slot_1 = offered[0].model_dump(mode="json")
    conv.state.booking_offered_slot_2 = (
        offered[1].model_dump(mode="json") if len(offered) > 1 else None
    )
    conv.state.booking_offered_slot_3 = None

    slots_display = format_slot_offer_display(offered)
    conv.state.booking_offered_slots_display = slots_display
    conv.write_metric("BOOKING_FLOW_SLOTS_OFFERED")

    plog.info(
        f"{log_prefix} offering display='{slots_display[:80]}' no_pref_match={no_pref_match} cell_phone_saved={cell_phone_saved}",
        is_pii=True,
    )

    flow.goto_step("Offer Booking Slot")

    saved_note = (
        "The cell phone number has been saved to the patient record. " if cell_phone_saved else ""
    )
    neighborhood_fallback = getattr(conv.state, "booking_neighborhood_fallback", False)
    nbr_utterance = (
        (
            "The patient's primary provider doesn't have any openings right now, but I do have some times available with another provider on their care team. "
            if is_cm
            else "Your primary provider doesn't have any openings right now, but I do have some times available with another provider on your care team. "
        )
        if neighborhood_fallback
        else ""
    )
    work_for = "Would one of those work?" if is_cm else "Would one of those work for you?"

    if no_pref_match:
        return {
            "utterance": f"{nbr_utterance}I wasn't able to find anything at that time, but I'm seeing {slots_display}. {work_for}",
            "content": saved_note,
        }
    return {
        "utterance": f"{nbr_utterance}Alright, I'm seeing {slots_display}. {work_for}",
        "content": saved_note,
    }
