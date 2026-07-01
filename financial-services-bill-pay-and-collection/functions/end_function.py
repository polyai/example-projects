import re

from _gen import *  # <AUTO GENERATED>

SMS_OFFER_RE = re.compile(
    r"\b(?:"
    r"would you like me to (?:send you|text you)|"
    r"i(?:'ll| will) (?:send|text)|"
    r"can send you|"
    r"can text you|"
    r"could you.*(?:send|text)|"
    r"if you'd like, i can (?:send|text)"
    r")\b.*?\b(?:sms|text)\b",
    flags=re.IGNORECASE,
)


HOW_CAN_I_HELP_RE = re.compile(
    r"\b(?:how can i help(?:\s+you)?|how may i help(?:\s+you)?|"
    r"what can i help(?:\s+you)?(?:\s+with)?|what can i do for you|"
    r"how can i assist(?:\s+you)?)\b",
    flags=re.IGNORECASE,
)


def pretty_print_call_history(call_history: list) -> str:
    """
    Pretty prints the call history in a readable format.

    Args:
        call_history: List of AgentResponse and UserInput objects

    Returns:
        Formatted string representation of the call history
    """
    formatted_history = []

    for i, entry in enumerate(call_history, 1):
        if hasattr(entry, "text"):
            if hasattr(entry, "__class__") and "AgentResponse" in str(entry.__class__):
                formatted_history.append(f"{i}. Agent: {entry.text}")
            elif hasattr(entry, "__class__") and "UserInput" in str(entry.__class__):
                formatted_history.append(f"{i}. User: {entry.text}")
            else:
                formatted_history.append(f"{i}. Unknown: {entry.text}")
        else:
            formatted_history.append(f"{i}. Unknown entry: {entry}")

    return "\n".join(formatted_history)


def log_metrics_via_llm(conv: Conversation):
    history_string = pretty_print_call_history(conv.history)
    metric_descriptions = {
        "FAQ_COMPLETED": (
            "An FAQ path has been completed, meaning that the call has gotten to the point "
            "where the Agent has asked the User if there is 'Anything else?'"
        ),
        "NO_INTERNET_APP_ACCESS": (
            "The user has stated that they do NOT have access to the internet, online banking, "
            "or the mobile app"
        ),
        "DIGITAL_NOT_WORKING": (
            "The user has said that online banking or the mobile app is NOT working correctly"
        ),
    }

    metric_definitions_string = "\n".join(f"- {k}: {v}" for k, v in metric_descriptions.items())
    return_format_string = "\n".join(f'\t"{k}": true/false,' for k in metric_descriptions.keys())

    prompt = f"""
A call between an Agent and a User was as follows:

{history_string}

Your task is to determine whether EACH of the following metrics occurred at any point during the call.

Metric definitions:
{metric_definitions_string}

Rules:
- Return ALL metrics, even if they did not occur.
- Use TRUE if the metric clearly occurred.
- Use FALSE if it did not occur or is ambiguous.
- Base your decision ONLY on the call transcript above.
- Do NOT add explanations or extra text.

You MUST return the result as a valid JSON in the following {{string : bool}} format:

{{
    {return_format_string}
}}
    """.strip()
    conv.log.info("Prompting for Metrics", prompt=prompt)
    try:
        metric_response = conv.utils.prompt_llm(prompt=prompt, return_json=True, model="gpt-5")
        conv.log.info("Received response", metric_response=metric_response)
        for metric, value in metric_response.items():
            if value:
                conv.write_metric(metric.upper(), write_once=True)
    except Exception as e:
        conv.log.warning("Error prompting LLM for Metrics", error=e)


TRANSFER_BOILERPLATE_RE = re.compile(
    r"(?:Transferring to .+?\.|Ringtone\.|Please wait while we transfer you.*?$)",
    flags=re.IGNORECASE | re.DOTALL,
)

HANDOFF_SUMMARY_PROMPT_TEMPLATE = """Handoff note for a Poly Bank agent picking up this call.

Conversation:
{history}

Write exactly 2-4 short points (each ≤20 words). Include specific details (amounts, names, dates) when mentioned. No redundancy — never restate the same fact. Never produce more than 4 points.

NEVER use these words: transfer, handoff, redirect, escalate, hold, connected, put through, awaiting, specialist. The receiving agent already knows the call was transferred.
Do NOT include action items or directives (e.g. "Need to verify...", "Awaiting next steps..."). Only state what the customer wants and what was established.
If the customer's request was unclear, state what they literally said — do not write "unclear phrasing" or "unspecified".

Focus on: why the customer called, what was established, and what they still need.

IMPORTANT: Separate points with /n. Do NOT use actual newlines between points.
No preamble, labels, bullet characters, or colons before points.

Good: Customer reports missing funds from personal account/nNo transaction details provided yet/nCustomer confirmed account is personal
Bad: Need to investigate missing funds and confirm recipient details/nAwaiting specialist to review transaction logs/nUrgent issue: money missing from account
Bad: Fraud concern: card transaction showing 0.00 amount/nNeed: connect to fraud team for resolution/nCustomer confirmed issue type: card transaction fraud"""


def _clean_history_for_summary(conv: Conversation) -> str:
    lines = []
    for entry in conv.history:
        text = (entry.text or "").strip()
        if not text:
            continue
        if hasattr(entry, "__class__") and "AgentResponse" in str(entry.__class__):
            text = TRANSFER_BOILERPLATE_RE.sub("", text).strip()
            if text:
                lines.append(f"Agent: {text}")
        elif hasattr(entry, "__class__") and "UserInput" in str(entry.__class__):
            lines.append(f"Customer: {text}")
    return "\n".join(lines)


def generate_handoff_reason_summary(conv: Conversation):
    if not conv.state.handoff_reason:
        return

    try:
        history = _clean_history_for_summary(conv)
        prompt = HANDOFF_SUMMARY_PROMPT_TEMPLATE.format(history=history)
        summary = conv.utils.prompt_llm(
            prompt=prompt,
            show_history=False,
            model="gpt-5-nano",
        )
        conv.state.handoff_reason_summary = summary.strip() if summary else ""
        conv.log.info("Handoff reason summary generated", summary=conv.state.handoff_reason_summary)
    except Exception as e:
        conv.log.error("Failed to generate handoff reason summary", error=str(e))


def end_function(conv: Conversation):
    # Evaluate whether the agent went off-script during the call
    try:
        unscripted_result = conv.functions.llm_unscripted_eval()
        if isinstance(unscripted_result, dict):
            is_unscripted = unscripted_result.get("unscripted", False)
            reason = unscripted_result.get("reason", "")
            conv.write_metric("IS_UNSCRIPTED", 1 if is_unscripted else 0)
            if is_unscripted and reason:
                conv.write_metric("UNSCRIPTED_REASON", str(reason)[:500])
        else:
            conv.log.warning("Unscripted eval returned unexpected result", result=unscripted_result)
            conv.write_metric("IS_UNSCRIPTED", "ERROR")
    except Exception as e:
        conv.log.error("Failed to run unscripted evaluation", error=str(e))
        conv.write_metric("IS_UNSCRIPTED", "ERROR")

    log_metrics_via_llm(conv)

    generate_handoff_reason_summary(conv)

    # # Store QA metrics, Handoff Reason, CRC and skill in memory
    # qa_metrics = list(
    #     (m.value for m in conv.metric_events if m.name == "QA")
    # )
    # sms_sent = any(list(
    #     (m.value for m in conv.metric_events if m.name == "SMS_SENT")
    # ))
    # conv.state["metric_engram"] = MetricEngram(
    #     qa_metrics=qa_metrics,
    #     sms_sent=sms_sent,
    #     handoff_reason=conv.state.handoff_reason,
    #     crc=conv.state.crc,
    #     handoff_to=conv.state.handoff_to,
    #     datetime=conv.state.formatted_date_time,
    #     conv_id=conv.id
    # ).json()

    # last event metrics
    flow_name = conv.current_flow
    step_name = conv.current_step
    last_qa_value = next((m.value for m in reversed(conv.metric_events) if m.name == "QA"), None)
    if flow_name and step_name:
        conv.write_metric("LAST_EVENT_TYPE", flow_name)
        conv.write_metric("LAST_EVENT", flow_name + " | " + step_name)
    elif last_qa_value:
        conv.write_metric("LAST_EVENT_TYPE", "QA")
        conv.write_metric("LAST_EVENT", last_qa_value)

    # speak to attempts
    conv.write_metric(
        "SPEAK_TO_ATTEMPTS", conv.state.speak_to_attempts if conv.state.speak_to_attempts else 0
    )

    # Per-turn Regex metrics
    for i, turn in enumerate(conv.history):
        if turn.role == "agent":
            if SMS_OFFER_RE.search(turn.text):
                conv.write_metric("SMS_OFFERED", write_once=True)

            if HOW_CAN_I_HELP_RE.search(turn.text or ""):
                conv.write_metric("HOW_CAN_I_HELP_ASKED")

                # Check whether the next turn is a user reply
                next_turn = conv.history[i + 1] if i + 1 < len(conv.history) else None
                if next_turn and next_turn.role == "user" and next_turn.text:
                    conv.write_metric("HOW_CAN_I_HELP_ANSWERED")
