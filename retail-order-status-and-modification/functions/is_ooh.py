from _gen import *  # <AUTO GENERATED>
from datetime import datetime
from zoneinfo import ZoneInfo


from .utterances import utterance


@func_description("Determines whether it's currently Out of Hours for call center.")
def is_ooh(conv: Conversation):
    status = (conv.state.center_status or "open").strip().lower()

    if status == "open":
        conv.state.ooh_utterance = None
        return False
    elif status == "closed":
        conv.state.ooh_utterance = utterance(conv, "ooh_closed")
        return True
    elif status == "holiday":
        conv.state.ooh_utterance = utterance(conv, "ooh_holiday")
        return True
    elif status == "emergency":
        conv.state.ooh_utterance = utterance(conv, "ooh_emergency")
        return True

    est_current_time = datetime.now(ZoneInfo("America/Chicago")).time()
    opening_time = datetime.strptime("06:00", "%H:%M").time()
    closing_time = datetime.strptime("23:59", "%H:%M").time()
    conv.state.ooh_utterance = utterance(conv, "ooh_fallback")
    return not (opening_time < est_current_time < closing_time)
