from _gen import *  # <AUTO GENERATED>
from functions import visits


def goodbye(conv) -> str:
    """The goodbye: 'we'll see you on Thursday' when a visit was booked or moved this call. A
    line that must be heard (a safety line) is said again first."""
    seen = conv.state.see_you_date
    if seen:
        day = visits.short_day(seen, visits.today(conv))
        when = day if day == "tomorrow" else f"on {day}"
        line = f"Thanks so much for calling, and we'll see you {when}!"
    else:
        line = "Thanks so much for calling, and have a lovely day!"
    must = conv.state.must_hear
    if must:
        conv.state.must_hear = ""
        return f"{must} {line}"
    return line


@func_description("End the call, once the caller has said there's nothing else.")
def hangup(conv: Conversation):
    conv.state.handoff_to = "CONTAINED"
    return {"utterance": goodbye(conv), "hangup": True}
