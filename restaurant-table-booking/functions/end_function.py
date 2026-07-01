import re

from _gen import *  # <AUTO GENERATED>


def end_function(conv: Conversation):
    flow_name = conv.current_flow
    step_name = conv.current_step

    if flow_name == "make_booking" and step_name == "Booking requires card details":
        conv.write_metric("ABANDON_AFTER_CC_HOLD")

    for turn in conv.history:
        if turn.role == "agent" and re.search(
            r"\b(?:would you like me to (?:send you|text you)|i(?:'ll| will) (?:send|text)|can send you|can text you|could you.*(?:send|text)|if you'd like, i can (?:send|text))\b.*?\b(?:sms|text)\b",
            turn.text,
            flags=re.IGNORECASE,
        ):
            conv.write_metric("SMS_OFFERED", write_once=True)
