from datetime import date, timedelta

from _gen import *  # <AUTO GENERATED>
from functions import appointments


def goodbye_line(conv) -> str:
    """'Thanks so much for calling, and we'll see you on Thursday. Take care!' after a booking
    or a move this call; otherwise 'Thanks so much for calling. Take care!'. A safety line
    spoken this call is said again first, so ending the call can't replace it."""
    line = "Thanks so much for calling. Take care!"
    visit = conv.state.visit_date
    if visit:
        day = date.fromisoformat(visit)
        tomorrow = appointments.today(conv) + timedelta(days=1)
        when = (
            "tomorrow"
            if day == tomorrow
            else f"on {appointments.WEEKDAYS[day.weekday()]}"
        )
        line = f"Thanks so much for calling, and we'll see you {when}. Take care!"
    must_hear = str(conv.state.must_hear or "").strip()
    return f"{must_hear} {line}" if must_hear else line


@func_description(
    "[Agent Behaviour] Say goodbye and end the call, once the caller has said they need nothing else. Say nothing yourself first."
)
def goodbye_and_hangup(conv: Conversation):
    conv.state.agent_hangup = True
    return {"utterance": goodbye_line(conv), "hangup": True}
