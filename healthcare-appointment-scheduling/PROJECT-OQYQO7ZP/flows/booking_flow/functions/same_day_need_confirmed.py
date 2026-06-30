import plog
from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


@func_description(
    "Called when the caller confirms they need to be seen today and no same-day slots are available. Transfers to scheduling."
)
def same_day_need_confirmed(conv: Conversation, flow: Flow) -> dict:
    log_prefix = "[same_day_need_confirmed]: "
    plog.info(f"{log_prefix} caller confirmed same-day need; handing off")
    conv.write_metric("BOOKING_SAME_DAY_CONFIRMED_NO_SLOTS")
    return handoff(
        conv,
        reason="BOOKING_NO_SAME_DAY_SLOTS",
        utterance=(
            "I'm not finding any openings for today. "
            "Let me transfer you to someone who can help get you scheduled. "
            "Putting you through now."
        ),
    )
