import plog
from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the caller says they do not specifically need a same-day appointment. Offers the pre-fetched future appointment slots."
)
def same_day_not_required(conv: Conversation, flow: Flow) -> dict:
    log_prefix = "[same_day_not_required]: "
    plog.info(f"{log_prefix} caller flexible on date; offering future slots")
    conv.write_metric("BOOKING_SAME_DAY_NOT_REQUIRED")

    slots_display = getattr(conv.state, "booking_offered_slots_display", "")
    if not slots_display:
        plog.info(f"{log_prefix} no slots display in state; unexpected")
        from functions.handoff import handoff

        return handoff(
            conv,
            reason="BOOKING_NO_SLOTS_AVAILABLE",
            utterance=(
                "I'm not seeing any available appointment times right now. "
                "Let me transfer you to someone who can help."
            ),
        )

    nbr = getattr(conv.state, "booking_neighborhood_fallback", False)
    nbr_part = (
        "Your primary provider doesn't have any openings right now, but I do have "
        "some times available with another provider on your care team. "
        if nbr
        else ""
    )

    flow.goto_step("Offer Booking Slot")
    return {
        "utterance": (
            f"{nbr_part}The next available times I'm seeing are "
            f"{slots_display}. Would one of those work for you?"
        )
    }
