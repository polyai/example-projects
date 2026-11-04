from _gen import *  # <AUTO GENERATED>
from functions import bookings

GOODBYE = "Thanks so much for calling, and have a lovely day!"
CSAT_QUESTION = "Before you go, did you get what you needed from this call today?"


def goodbye(conv) -> str:
    """'Thanks so much for calling, and we'll see you on Friday!' after a booking this call."""
    booked = conv.state.booked_date
    if booked:
        try:
            return f"Thanks so much for calling, and we'll see you {bookings.goodbye_day(conv, booked, conv.state.booked_time or '')}!"
        except ValueError:
            pass
    return GOODBYE


@func_description(
    "The caller has nothing else: end the call. Call it when they say no to 'Is there anything else I can help with?' or say goodbye."
)
def end_call(conv: Conversation):
    # A done line spoken in this same turn would be replaced by the goodbye: say it first.
    first = bookings.unheard_line(conv)
    lead = (
        f"{first.removesuffix(' Is there anything else I can help with?')} "
        if first
        else ""
    )
    # settings.csat_enabled (default false; the older top-level csat_enabled also works): ask one
    # satisfaction question before hanging up.
    legacy = bool((conv.real_time_config or {}).get("csat_enabled", False))
    enabled = bookings.is_true(str(bookings.setting(conv, "csat_enabled", legacy)))
    if enabled and not conv.state.csat_asked:
        conv.state.csat_asked = True
        conv.write_metric("CSAT_OFFERED")
        return {
            "utterance": lead + CSAT_QUESTION,
            "content": "When they answer, call log_csat_response.",
        }
    return {"utterance": lead + goodbye(conv), "hangup": True}
