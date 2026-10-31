import re

from _gen import *  # <AUTO GENERATED>


def end_function(conv: Conversation):
    for turn in conv.history:
        if turn.role == "agent" and re.search(
            r"\b(?:would you like me to (?:send you|text you)|i(?:'ll| will) (?:send|text)|can send you|can text you|if you'd like, i can (?:send|text))\b.*?\b(?:sms|text|link)\b",
            turn.text,
            flags=re.IGNORECASE,
        ):
            conv.write_metric("SMS_OFFERED", write_once=True)
            break
    if conv.current_flow == "make_booking" and not conv.state.booked_booking_id:
        conv.write_metric("ABANDONED_MAKE_BOOKING", write_once=True)
