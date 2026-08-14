"""End-of-call processing.

Generates a handoff summary (if a transfer occurred) and records
final metrics for analytics.
"""

from _gen import *  # <AUTO GENERATED>

HANDOFF_SUMMARY_PROMPT_TEMPLATE = """Handoff note for an agent picking up this call.

Conversation:
{history}

Write exactly 2-4 short points (each <=20 words). Include specific details
(amounts, names, dates) when mentioned. No redundancy.

Focus on: why the customer called, what was established, and what they still need.

IMPORTANT: Separate points with /n. Do NOT use actual newlines between points.
No preamble, labels, bullet characters, or colons before points.

Good: Customer wants to make a payment to a new recipient/nNo payment details provided yet
Bad: Need to verify payment details/nAwaiting specialist review"""


def _clean_history_for_summary(conv: Conversation) -> str:
    lines = []
    for entry in conv.history:
        text = (entry.text or "").strip()
        if not text:
            continue
        if hasattr(entry, "__class__") and "AgentResponse" in str(entry.__class__):
            lines.append(f"Agent: {text}")
        elif hasattr(entry, "__class__") and "UserInput" in str(entry.__class__):
            lines.append(f"Customer: {text}")
    return "\n".join(lines)


def generate_handoff_reason_summary(conv: Conversation):
    """Use an LLM to produce a concise handoff summary for the receiving agent."""
    if not conv.state.handoff_reason:
        return
    try:
        history = _clean_history_for_summary(conv)
        prompt = HANDOFF_SUMMARY_PROMPT_TEMPLATE.format(history=history)
        summary = conv.utils.prompt_llm(
            prompt=prompt, show_history=False, model="gpt-5-nano"
        )
        conv.state.handoff_reason_summary = summary.strip() if summary else ""
        conv.log.info(
            "Handoff summary generated", summary=conv.state.handoff_reason_summary
        )
    except Exception as e:
        conv.log.error("Failed to generate handoff summary", error=str(e))


def end_function(conv: Conversation):
    # Generate handoff summary if the call was transferred
    generate_handoff_reason_summary(conv)

    # Record which flow/step or FAQ was active at end of call
    flow_name = conv.current_flow
    step_name = conv.current_step
    last_qa_value = next(
        (m.value for m in reversed(conv.metric_events) if m.name == "QA"), None
    )

    if flow_name and step_name:
        conv.write_metric("LAST_EVENT_TYPE", flow_name)
        conv.write_metric("LAST_EVENT", flow_name + " | " + step_name)
    elif last_qa_value:
        conv.write_metric("LAST_EVENT_TYPE", "QA")
        conv.write_metric("LAST_EVENT", last_qa_value)

    # Speak-to attempts counter
    conv.write_metric(
        "SPEAK_TO_ATTEMPTS",
        conv.state.speak_to_attempts if conv.state.speak_to_attempts else 0,
    )
