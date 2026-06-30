"""Called when the caller states a scheduling preference; finds 3 matching slots and offers them."""

from typing import Any

import plog
from _gen import *  # <AUTO GENERATED>
from functions.extract_time_preference import extract_time_preference_from_conversation
from functions.handoff import handoff
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import (
    format_slot_offer_display,
    get_top_n_available_slots,
    get_top_n_preference_slots,
)


@func_description(
    "Called after the caller states a scheduling preference in the Collect Booking Preference step. Extracts the preference from the conversation and offers up to 3 matching slots."
)
def booking_preference_provided(conv: Conversation, flow: Flow) -> dict[str, Any]:
    """Find 3 slots matching the caller's stated preference and offer them."""
    log_prefix = "[booking_preference_provided.booking_preference_provided]: "
    plog.info(f"{log_prefix} entered")

    # Filter out slots already declined in this session
    declined_starts: list[str] = list(
        getattr(conv.state, "booking_declined_slot_starts", None) or []
    )
    raw_slots = getattr(conv.state, "booking_available_slots", None) or []
    all_slots = [AppointmentSlot.model_validate(s) for s in raw_slots]
    remaining = [s for s in all_slots if str(s.start_date or "") not in declined_starts]
    plog.info(f"{log_prefix} remaining_slot_count={len(remaining)}")

    if not remaining:
        plog.info(f"{log_prefix} no remaining slots; handing off")
        conv.write_metric("BOOKING_FLOW_NO_MORE_SLOTS")
        return handoff(
            conv,
            reason="BOOKING_NO_REMAINING_SLOTS",
            utterance="I'm not finding any available times in the next 90 days. Let me transfer you to someone who can help.",
        )

    # Extract the preference the caller just stated (most recent in conversation history)
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
            slots=remaining,
            n=3,
        )
        if not offered:
            no_pref_match = True
            conv.state.booking_no_pref_match_confirmed = True
            offered = get_top_n_available_slots(remaining, n=3)
            plog.info(
                f"{log_prefix} no pref match; falling back to {len(offered)} available slot(s)"
            )
        else:
            plog.info(f"{log_prefix} preference matched {len(offered)} slot(s)")
    else:
        offered = get_top_n_available_slots(remaining, n=3)
        plog.info(f"{log_prefix} no preference extracted; offering {len(offered)} earliest slot(s)")

    if not offered:
        plog.info(f"{log_prefix} no slots available after selection; handing off")
        conv.write_metric("BOOKING_FLOW_NO_MORE_SLOTS")
        return handoff(
            conv,
            reason="BOOKING_NO_REMAINING_SLOTS",
            utterance="I'm not finding any more available times in the next 90 days. Let me transfer you to someone who can help.",
        )

    # Store up to 3 offered slots in state
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
        f"{log_prefix} offering display='{slots_display[:80]}' no_pref_match={no_pref_match}",
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
