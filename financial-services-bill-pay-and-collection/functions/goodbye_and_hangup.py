from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Agent Behaviour] Say goodbye and end the conversation if and only if you've explicitly confirmed with the user that they don't need help with anything else"
)
def goodbye_and_hangup(conv: Conversation):
    if conv.current_step == "Ask Urgent":
        return {
            "utterance": "Ok, please call back during our opening hours from 9am to 6pm Monday to Friday when we can help you, except on bank holidays where this will vary. Thanks for calling Poly Bank, goodbye!",
            "hangup": True,
        }
    flags = conv.real_time_config.get("flags", {})
    if flags.get("csat_enabled") and not conv.state.csat_offered:
        conv.write_metric("CSAT_OFFERED")
        conv.state.csat_offered = True
        conv.goto_flow("CSAT")
        return {
            "utterance": "Ok, if there's nothing else I can help with, would you be ok to quickly share some feedback on your experience today?"
        }
    if conv.current_flow == "CSAT":
        conv.write_metric("CSAT_REFUSED")
        return {
            "utterance": "No problem. I hope you have a great rest of your day. Goodbye!",
            "hangup": True,
        }
    return {"utterance": "Okay. I hope you have a great rest of your day. Goodbye!", "hangup": True}
