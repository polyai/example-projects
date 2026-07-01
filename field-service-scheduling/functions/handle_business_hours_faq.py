from _gen import *  # <AUTO GENERATED>
from functions.utils import opening_hours_utterance


@func_description(
    "Call this function when the user asks about business hours or when the office is open."
)
def handle_business_hours_faq(conv: Conversation):
    if conv.state.routing_enabled:
        return conv.functions.route_call("GENERAL_QUESTION")

    try:
        hours = opening_hours_utterance(conv.real_time_config.get("opening_hours", {}))
    except Exception:
        hours = ""
        conv.log.error("error parsing business hours", exc_info=True)

    if hours:
        return {"content": hours}

    return {
        "content": "I'm sorry, I don't have the current business hours available right now. You can check our website or give us a call back for that information."
    }
