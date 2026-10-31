from _gen import *  # <AUTO GENERATED>
from functions import hours


@func_description(
    "[Agent Behaviour] Say goodbye and end the conversation if and only if you've explicitly confirmed with the user that they don't need help with anything else"
)
def goodbye_and_hangup(conv: Conversation):
    company = (
        (getattr(conv.variant, "site_name", "") or "").strip() if conv.variant else ""
    )
    thanks = (
        f"Thanks for calling {company}, goodbye!"
        if company
        else "Thanks for calling, goodbye!"
    )
    if conv.current_flow == "out_of_hours":
        if hours.has_hours(conv):
            call_back = (
                f"Okay, please call back during our opening hours, {hours.say_hours(conv)}, "
                "and we'll help you then."
            )
        else:
            call_back = (
                "Okay, please call back when we're open and we'll help you then. "
                + hours.not_to_hand(conv)
            )
        return {"utterance": f"{call_back} {thanks}", "hangup": True}
    flags = (conv.real_time_config or {}).get("flags", {}) or {}
    if flags.get("csat_enabled") and not conv.state.csat_offered:
        conv.write_metric("CSAT_OFFERED")
        conv.state.csat_offered = True
        conv.goto_flow("CSAT")
        return {
            "utterance": "Ok, if there's nothing else I can help with, would you be ok to quickly share some feedback on your experience today?"
        }
    if conv.current_flow == "CSAT":
        conv.write_metric("CSAT_REFUSED")
        return {"utterance": f"No problem. {thanks}", "hangup": True}
    return {
        "utterance": f"Okay. I hope you have a great rest of your day. {thanks}",
        "hangup": True,
    }
