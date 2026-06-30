"""Called when the caller declines the offered slots; routes to preference collection or offers 3 more."""

from datetime import UTC, datetime, timedelta
from typing import Any

import plog
from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import (
    get_blocked_booking_dates,
    get_recall_window,
    is_recheck_type,
)
from functions.extract_time_preference import extract_time_preference_from_conversation
from functions.fetch_available_slots import (
    _FOLLOW_UP_CATEGORY_ID,
    _apply_booking_filters,
    _fetch_neighborhood_slots,
    fetch_booking_slots_for_state,
)
from functions.get_grace_nextgen_api_handler import get_grace_nextgen_api_handler
from functions.handoff import handoff
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import (
    format_slot_offer_display,
    get_top_n_available_slots,
    get_top_n_preference_slots,
)


@func_description(
    "Called when the caller declines the offered booking slots and wants different times. Routes to preference collection if no preference is known, otherwise offers 3 more slots."
)
def booking_slot_declined(conv: Conversation, flow: Flow) -> dict[str, Any]:
    """Decide next step after the caller declines: collect preference or offer 3 more slots."""
    log_prefix = "[booking_slot_declined.booking_slot_declined]: "
    plog.info(f"{log_prefix} flow_current_step={getattr(flow, 'current_step', None)!r}")
    conv.write_metric("BOOKING_FLOW_SLOT_DECLINED")

    decline_count = (getattr(conv.state, "booking_slot_decline_count", None) or 0) + 1
    conv.state.booking_slot_decline_count = decline_count
    plog.info(f"{log_prefix} decline_count={decline_count}")

    if decline_count >= 2:
        plog.info(f"{log_prefix} decline limit reached; transferring to scheduling")
        conv.write_metric("BOOKING_FLOW_DECLINE_LIMIT_REACHED")
        return handoff(
            conv,
            reason="BOOKING_NO_SLOTS_AVAILABLE",
            utterance=(
                "I haven't been able to find a time that works for you. "
                "Let me transfer you to our scheduling team — they'll have "
                "more options available. Putting you through now."
            ),
        )

    # Mark all currently offered slots as declined
    declined_starts: list[str] = list(
        getattr(conv.state, "booking_declined_slot_starts", None) or []
    )
    for slot_key in (
        "booking_offered_slot_1",
        "booking_offered_slot_2",
        "booking_offered_slot_3",
    ):
        slot_data = getattr(conv.state, slot_key, None)
        if slot_data:
            slot = AppointmentSlot.model_validate(slot_data)
            start_str = str(slot.start_date or "")
            if start_str and start_str not in declined_starts:
                declined_starts.append(start_str)
    conv.state.booking_declined_slot_starts = declined_starts
    plog.info(f"{log_prefix} declined_starts_count={len(declined_starts)}")

    # Check remaining availability
    raw_slots = getattr(conv.state, "booking_available_slots", None) or []
    all_slots = [AppointmentSlot.model_validate(s) for s in raw_slots]
    remaining = [s for s in all_slots if str(s.start_date or "") not in declined_starts]
    plog.info(f"{log_prefix} remaining_slot_count={len(remaining)}")

    if not remaining:
        # If we were using SD slots and they're exhausted, fall back to regular FP/IM
        if getattr(conv.state, "booking_used_same_day_category", False):
            plog.info(f"{log_prefix} SD slots exhausted; falling back to regular FP/IM")
            conv.state.booking_used_same_day_category = False
            fetch_booking_slots_for_state(conv)
            fallback_raw = getattr(conv.state, "booking_available_slots", None) or []
            fallback_slots = [AppointmentSlot.model_validate(s) for s in fallback_raw]
            fallback_remaining = [
                s for s in fallback_slots if str(s.start_date or "") not in declined_starts
            ]
            if fallback_remaining:
                plog.info(
                    f"{log_prefix} regular FP/IM fallback: {len(fallback_remaining)} slot(s) available"
                )
                offered = get_top_n_available_slots(fallback_remaining, n=3)
                return _offer_slots(conv, flow, offered, no_pref_match=False)
            plog.info(f"{log_prefix} regular FP/IM fallback: no slots either")

        nbr_already_tried = bool(getattr(conv.state, "booking_neighborhood_fallback", False))
        if not nbr_already_tried:
            plog.info(f"{log_prefix} no remaining primary slots; trying neighborhood providers")

            neighborhood_fetch_failed = False

            start_iso = getattr(conv.state, "booking_slot_search_start_iso", None) or None
            end_iso = getattr(conv.state, "booking_slot_search_end_iso", None) or None
            category_id = (
                getattr(conv.state, "booking_slot_search_category_id", None)
                or _FOLLOW_UP_CATEGORY_ID
            )

            appt_type = getattr(conv.state, "booking_appointment_type", None) or ""
            if (not start_iso or not end_iso) and is_recheck_type(appt_type):
                recall = get_recall_window(conv, appt_type)
                if recall.ok:
                    start_iso = recall.start_iso
                    end_iso = recall.end_iso

            try:
                resource_id = getattr(conv.state, "patient_resource_id", None) or None
                handler = get_grace_nextgen_api_handler(conv)
                now = datetime.now(UTC)
                start_iso = start_iso or now.strftime("%Y-%m-%dT00:00:00")
                end_iso = end_iso or (now + timedelta(days=90)).strftime("%Y-%m-%dT23:59:59")

                nbr_raw = _fetch_neighborhood_slots(
                    conv,
                    handler,
                    resource_id,
                    start_iso,
                    end_iso,
                    category_id,
                )
                language_barrier = bool(getattr(conv.state, "patient_language_barrier", False))
                blocked_dates = get_blocked_booking_dates(conv, start_iso, end_iso)
                nbr_slots = _apply_booking_filters(nbr_raw, now, language_barrier, blocked_dates)

                if nbr_slots:
                    conv.state.booking_neighborhood_fallback = True

                    # Filter out already-declined start times so we don't re-offer duplicates
                    # across provider fallback.
                    nbr_remaining = [
                        s for s in nbr_slots if str(s.start_date or "") not in declined_starts
                    ]

                    dumped = [s.model_dump(mode="json") for s in nbr_slots]
                    conv.state.booking_available_slots = dumped
                    conv.state.booking_no_pref_match_confirmed = False
                    conv.write_metric("BOOKING_FLOW_SLOTS_LOADED", len(nbr_slots))

                    offered = get_top_n_available_slots(nbr_remaining, n=3)
                    return _offer_slots(conv, flow, offered, no_pref_match=False)
            except Exception as e:
                neighborhood_fetch_failed = True
                plog.info(f"{log_prefix} neighborhood fetch failed: {e}")
                conv.log.error(
                    "Booking slot declined: neighborhood fetch failed",
                    error=str(e),
                    resource_id=resource_id,
                    start_iso=start_iso,
                    end_iso=end_iso,
                    category_id=category_id,
                )
                conv.write_metric("BOOKING_FLOW_NEIGHBORHOOD_FETCH_FAILED")

            if neighborhood_fetch_failed:
                return handoff(
                    conv,
                    reason="BOOKING_SLOT_LOOKUP_FAILED_NEIGHBORHOOD",
                    utterance=(
                        "I'm not finding any more available times in the next 90 days. "
                        "Let me transfer you to someone who can help."
                    ),
                )

        plog.info(f"{log_prefix} no remaining slots; handing off")
        conv.write_metric("BOOKING_FLOW_NO_MORE_SLOTS")
        return handoff(
            conv,
            reason="BOOKING_NO_REMAINING_SLOTS",
            utterance=(
                "I'm not finding any more available times in the next 90 days. "
                "Let me transfer you to someone who can help."
            ),
        )

    # Re-check latest preference from conversation history
    pref = extract_time_preference_from_conversation(conv)
    no_pref_match_confirmed = bool(getattr(conv.state, "booking_no_pref_match_confirmed", False))

    plog.info(
        f"{log_prefix} pref.has_preference={pref.has_preference} "
        f"no_pref_match_confirmed={no_pref_match_confirmed}"
    )

    # --- CASE 1: No preference known → ask for one ---
    if not pref.has_preference:
        plog.info(f"{log_prefix} no preference; routing to Collect Booking Preference")
        flow.goto_step("Collect Booking Preference")
        return {
            "content": (
                "The caller declined the offered slot(s) and has no scheduling preference on record. "
                "Ask when they'd like to come in — they can share a preferred day, time of day, "
                "or specific date."
            )
        }

    # --- CASE 2: Preference known but already confirmed no match → offer 3 available ---
    if no_pref_match_confirmed:
        offered = get_top_n_available_slots(remaining, n=3)
        plog.info(
            f"{log_prefix} no_pref_match_confirmed; offering {len(offered)} available slot(s)"
        )
        return _offer_slots(conv, flow, offered, no_pref_match=False)

    # --- CASE 3: Preference known, try to match 3 slots ---
    offered = get_top_n_preference_slots(
        requested_date=pref.requested_date,
        requested_time=pref.requested_time,
        slots=remaining,
        n=3,
    )
    if not offered:
        # No match — fall back to 3 available, flag so we don't retry
        conv.state.booking_no_pref_match_confirmed = True
        offered = get_top_n_available_slots(remaining, n=3)
        plog.info(f"{log_prefix} no pref match; falling back to {len(offered)} available slot(s)")
        return _offer_slots(conv, flow, offered, no_pref_match=True)

    plog.info(f"{log_prefix} preference matched {len(offered)} slot(s)")
    return _offer_slots(conv, flow, offered, no_pref_match=False)


def _offer_slots(
    conv: Conversation,
    flow: Flow,
    offered: list[AppointmentSlot],
    no_pref_match: bool,
) -> dict[str, Any]:
    """Store up to 3 offered slots in state and transition to Offer Booking Slot."""
    log_prefix = "[booking_slot_declined._offer_slots]: "

    if not offered:
        plog.info(f"{log_prefix} offered list empty after selection; handing off")
        conv.write_metric("BOOKING_FLOW_NO_MORE_SLOTS")
        return handoff(
            conv,
            reason="BOOKING_NO_REMAINING_SLOTS",
            utterance=(
                "I'm not finding any more available times in the next 90 days. "
                "Let me transfer you to someone who can help."
            ),
        )

    conv.state.booking_offered_slot_1 = offered[0].model_dump(mode="json")
    conv.state.booking_offered_slot_2 = (
        offered[1].model_dump(mode="json") if len(offered) > 1 else None
    )
    conv.state.booking_offered_slot_3 = (
        offered[2].model_dump(mode="json") if len(offered) > 2 else None
    )

    slots_display = format_slot_offer_display(offered)
    conv.state.booking_offered_slots_display = slots_display
    conv.write_metric("BOOKING_FLOW_SLOTS_OFFERED")

    plog.info(
        f"{log_prefix} display='{slots_display[:80]}' no_pref_match={no_pref_match}",
        is_pii=True,
    )

    flow.goto_step("Offer Booking Slot")

    if no_pref_match:
        return {
            "utterance": (
                f"I wasn't able to find anything at that time, but I'm seeing "
                f"{slots_display}. Would one of those work for you?"
            )
        }
    return {
        "utterance": f"How about {slots_display}? Would one of those work for you?",
    }
