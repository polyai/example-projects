from _gen import *  # <AUTO GENERATED>

EMERGENCY_LINE = "Please hang up and call 911."


@func_description(
    "An emergency, danger, or anyone at risk of harm. Call it straight away, before anything else."
)
def emergency(conv: Conversation):
    conv.write_metric("EMERGENCY", write_once=True)
    conv.state.must_hear = EMERGENCY_LINE
    return {"utterance": EMERGENCY_LINE}
