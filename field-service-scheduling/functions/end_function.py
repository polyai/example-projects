import re

from _gen import *  # <AUTO GENERATED>


def end_function(conv: Conversation):
    for turn in conv.history:
        if turn.role == "agent" and re.search(
            r"\b(?:would you like me to (?:send you|text you)|i(?:'ll| will) (?:send|text)|can send you|can text you|could you.*(?:send|text)|if you'd like, i can (?:send|text))\b.*?\b(?:sms|text)\b",
            turn.text,
            flags=re.IGNORECASE,
        ):
            conv.write_metric("SMS_OFFERED", write_once=True)
