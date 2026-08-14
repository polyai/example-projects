"""Called when the caller declines the offered slots; offers 3 more or hands off."""

from typing import Any

import plog

from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import (
    format_slot_offer_display,
    get_top_n_available_slots,
)


@func_description(
    "Called when the caller declines the offered booking slots and wants different times."
)
def booking_slot_declined(conv: Conversation, flow: Flow) -> dict[str, Any]:
    """Offer 3 more slots from the remaining pool, or hand off if exhausted."""
    log_prefix = "[booking_slot_declined]: "
    conv.write_metric("BOOKING_FLOW_SLOT_DECLINED", True)

    decline_count = (getattr(conv.state, "booking_slot_decline_count", None) or 0) + 1
    conv.state.booking_slot_decline_count = decline_count
    plog.info(f"{log_prefix} decline_count={decline_count}")

    if decline_count >= 2:
        plog.info(f"{log_prefix} decline limit reached; transferring")
        return handoff(
            conv,
            reason="BOOKING_NO_SLOTS_AVAILABLE",
            utterance=(
                "I haven't been able to find a time that works for you. "
                "Let me transfer you to our scheduling team. Putting you through now."
            ),
        )

    # Mark currently offered slots as declined
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

    # Filter remaining slots
    raw_slots = getattr(conv.state, "booking_available_slots", None) or []
    all_slots = [AppointmentSlot.model_validate(s) for s in raw_slots]
    remaining = [s for s in all_slots if str(s.start_date or "") not in declined_starts]

    if not remaining:
        plog.info(f"{log_prefix} no remaining slots; handing off")
        return handoff(
            conv,
            reason="BOOKING_NO_REMAINING_SLOTS",
            utterance=(
                "I'm not finding any more available times. "
                "Let me transfer you to someone who can help."
            ),
        )

    # Offer up to 3 more slots
    offered = get_top_n_available_slots(remaining, n=3)
    if not offered:
        return handoff(
            conv,
            reason="BOOKING_NO_REMAINING_SLOTS",
            utterance="I'm not finding any more available times. Let me transfer you to someone who can help.",
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
    conv.write_metric("BOOKING_FLOW_SLOTS_OFFERED", True)

    flow.goto_step("Offer Booking Slot")
    return {"utterance": f"How about {slots_display}? Would one of those work for you?"}
