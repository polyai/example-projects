import re

from _gen import *  # <AUTO GENERATED>


def end_function(conv: Conversation):
    log_prefix = "end_function:"
    agent_hangup = getattr(conv.state, "agent_hangup", None)
    conv.log.info(f"{log_prefix} agent_hangup", agent_hangup=agent_hangup)
    if not agent_hangup:
        conv.write_metric("USER_HANGUP")

    # SMS offered metrics
    for turn in conv.history:
        if turn.role == "agent" and re.search(
            r"\b(?:would you like me to|i(?:'ll| will)|i can|can|if you'd like,? i can)\s+(?:text you|send you\b.*?\b(?:text|sms))\b",
            turn.text,
            flags=re.IGNORECASE,
        ):
            conv.write_metric("SMS_OFFERED", write_once=True)

    # Last event metrics
    flow_name = conv.current_flow
    step_name = conv.current_step
    last_qa_value = next((m.value for m in reversed(conv.metric_events) if m.name == "QA"), None)
    if flow_name and step_name:
        conv.write_metric("LAST_EVENT_TYPE", flow_name)
        conv.write_metric("LAST_EVENT", flow_name + " | " + step_name)
    elif last_qa_value:
        conv.write_metric("LAST_EVENT_TYPE", "QA")
        conv.write_metric("LAST_EVENT", last_qa_value)
