from _gen import *  # <AUTO GENERATED>


@func_description("Call after the user says they don't need help with anything else.")
def ask_csat(conv: Conversation):
    if not conv.real_time_config.get("csat_enabled"):
        return {"utterance": "Enjoy the rest of your day! Goodbye!", "hangup": True}
    conv.write_metric("CSAT_OFFERED", value=None, write_once=False)
    conv.goto_flow("csat")
    return {
        "utterance": "Before you go, did you get what you needed from this call today?",
        "transition": {"goto_flow": "csat"},
    }
