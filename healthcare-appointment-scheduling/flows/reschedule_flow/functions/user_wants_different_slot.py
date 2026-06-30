from typing import Any

import plog
from _gen import *  # <AUTO GENERATED>
from functions.extract_time_preference import extract_time_preference_from_conversation
from functions.handoff import handoff
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import (
    format_slot_display,
    get_next_available_slot,
    select_closest_slot,
)


@func_description(
    "Called when the user declines the offered slot and wants a different time; removes the current offer, applies any updated preference, and re-offers the next best slot."
)
def user_wants_different_slot(conv: Conversation, flow: Flow) -> dict[str, Any]:
    """Find and offer the next best slot after the user declines the current one."""
    log_prefix = "[user_wants_different_slot.user_wants_different_slot]: "
    plog.info(f"{log_prefix} flow_current_step={getattr(flow, 'current_step', None)!r}")
    conv.write_metric("RESCHEDULE_FLOW_SLOT_DECLINED")

    # Record the declined slot so we don't re-offer it
    offered_slot_data = getattr(conv.state, "reschedule_offered_slot", None)
    declined_starts: list[str] = getattr(conv.state, "reschedule_declined_slot_starts", None) or []
    if offered_slot_data:
        declined_slot = AppointmentSlot.model_validate(offered_slot_data)
        if declined_slot.start_date and str(declined_slot.start_date) not in declined_starts:
            declined_starts = list(declined_starts) + [str(declined_slot.start_date)]
    conv.state.reschedule_declined_slot_starts = declined_starts
    plog.info(f"{log_prefix} declined_starts_count={len(declined_starts)}")

    # Filter available slots to remove all previously declined times
    raw_slots = getattr(conv.state, "reschedule_available_slots", None) or []
    all_slots = [AppointmentSlot.model_validate(s) for s in raw_slots]
    remaining = [s for s in all_slots if str(s.start_date or "") not in declined_starts]
    plog.info(f"{log_prefix} remaining_slot_count={len(remaining)}")

    if not remaining:
        plog.info(f"{log_prefix} no remaining slots; handing off")
        conv.write_metric("RESCHEDULE_FLOW_NO_MORE_SLOTS")
        return handoff(
            conv,
            reason="RESCHEDULE_NO_REMAINING_SLOTS",
            utterance="I'm not finding any more available times in the next 90 days. Let me transfer you to someone who can help.",
        )

    # Re-extract preference — the user may have expressed a new one in their latest turn
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
            slots=remaining,
        )
        if offered is None:
            offered = get_next_available_slot(remaining)
            no_pref_match = True
            plog.info(f"{log_prefix} no pref match; falling back to next available")
    else:
        offered = get_next_available_slot(remaining)
        plog.info(f"{log_prefix} no preference; offering next available")

    if offered is None:
        plog.info(f"{log_prefix} no slot selected after preference check; handing off")
        conv.write_metric("RESCHEDULE_FLOW_NO_MORE_SLOTS")
        return handoff(
            conv,
            reason="RESCHEDULE_NO_REMAINING_SLOTS",
            utterance="I'm not finding any more available times in the next 90 days. Let me transfer you to someone who can help.",
        )

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
    conv.state.reschedule_offered_slot_display = format_slot_display(
        offered, provider_name=_provider_name
    )
    plog.info(
        f"{log_prefix} new_offered_slot_start='{offered.start_date}' "
        f"display='{conv.state.reschedule_offered_slot_display}'",
        is_pii=True,
    )
    conv.write_metric("RESCHEDULE_FLOW_SLOT_OFFERED")

    flow.goto_step("Offer Slot")

    display = conv.state.reschedule_offered_slot_display

    if no_pref_match:
        return {
            "content": (
                f"No slots matched the caller's updated preference. "
                f"Offer the next available time instead: {display}. Ask if this works for them."
            )
        }
    return {
        "content": (
            f"The caller declined the previous slot. Offer this alternative: {display}. "
            "Ask if this works for them."
        )
    }
