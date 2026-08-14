from _gen import *  # <AUTO GENERATED>
import json
import re
from typing import Optional


from .create_call_summary import call_under_5s
from .kb_constants import KB_TOPIC_TO_CONTACT_REASON_MAPPING

HANGUP_CALL_SUMMARY_PROMPT = (
    "Your task is to briefly summarize the given call between a caller and a "
    "virtual assistant. The call_summary will be read by a real human agent after the call, "
    "so please include what the caller is trying to do or ask for, and how the virtual assistant "
    "attempted to help them.\n\n"
    "The output must be valid JSON with exactly this key:\n"
    "{\n"
    '  "call_summary": "<1-2 sentence summary>"\n'
    "}\n\n"
    "The call_summary should be brief, using only 1 or 2 sentences that concisely describe the purpose of the call, "
    "and must not contain any personal identifying information (such as the caller's name)."
)


def _extract_json_from_text(text: str) -> str:
    if not text:
        return text
    s = text.strip()

    # Strip fenced code blocks
    m = re.search(r"```(?:json)?\s*(.+?)\s*```", s, flags=re.DOTALL | re.IGNORECASE)
    if m:
        s = m.group(1).strip()

    if not s.lstrip().startswith("{"):
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            s = s[start : end + 1].strip()

    return s


def _get_matched_topic_from_qa(conv: Conversation) -> Optional[str]:
    """Extract matched topic from QA metrics if available."""
    try:
        qa_values = [m.value for m in conv.metric_events if "QA" in m.name and m.value]

        if not qa_values:
            return None

        for qa_value in reversed(qa_values):
            if (
                qa_value.startswith("General_Behavior")
                and qa_value != "General_Behavior-handoff_deflection"
            ):
                continue

            if qa_value in KB_TOPIC_TO_CONTACT_REASON_MAPPING:
                conv.log.info(
                    "Found matched topic from QA value",
                    qa_value=qa_value,
                    call_id=conv.id,
                )
                return qa_value

        conv.log.info(
            "QA values found but none mapped to valid topics",
            qa_values=qa_values,
            call_id=conv.id,
        )
        return None
    except Exception as e:
        conv.log.error(
            "Error extracting QA values for topic matching",
            error=str(e),
            call_id=conv.id,
        )
        return None


def end_function(conv: Conversation):
    # --- Generate call summary if not already set ---
    if not conv.state.summary_added:
        matched_topic_from_qa = _get_matched_topic_from_qa(conv)

        summary_text = ""
        matched_topic = None
        llm_failed = False
        raw_response = None

        try:
            raw_response = conv.utils.prompt_llm(
                HANGUP_CALL_SUMMARY_PROMPT, show_history=True
            )
            conv.log.info(
                "LLM call completed",
                raw_response_length=len(raw_response) if raw_response else 0,
            )

            safe_json = _extract_json_from_text(raw_response)
            parsed = json.loads(safe_json)
            summary_text = parsed.get("call_summary", "").strip()

            matched_topic = matched_topic_from_qa or "DEFAULT"
        except json.JSONDecodeError as e:
            llm_failed = True
            conv.log.error("Failed to parse LLM summary JSON", error=str(e))
            matched_topic = matched_topic_from_qa or "DEFAULT"
        except Exception as e:
            llm_failed = True
            conv.log.error("LLM call failed", error=str(e), error_type=type(e).__name__)
            matched_topic = matched_topic_from_qa or "DEFAULT"

        if not matched_topic:
            matched_topic = matched_topic_from_qa or "DEFAULT"

        is_verified = bool(conv.state.verified or conv.state.idnv_passed)
        prefix = "VERIFIED USER" if is_verified else "UNVERIFIED USER"

        conv.state.call_summary = (
            f"{prefix} - {summary_text}" if summary_text else prefix
        )
        conv.state.matched_topic = matched_topic

        conv.log.info(
            "Set matched topic and call summary",
            matched_topic=matched_topic,
            call_summary=conv.state.call_summary,
            llm_failed=llm_failed,
            call_id=conv.id,
        )

    # --- Check whether we offered SMS ---
    for turn in conv.history:
        if turn.role == "agent" and re.search(
            r"\b(?:would you like me to (?:send you|text you)|i(?:'ll| will) (?:send|text)|can send you|can text you|could you.*(?:send|text)|if you'd like, i can (?:send|text))\b.*?\b(?:sms|text)\b",
            turn.text,
            flags=re.IGNORECASE,
        ):
            conv.write_metric("SMS_OFFERED", write_once=True)

    # --- Determine contact reason ---
    if conv.state.handoff_reason in ["ESCALATION"]:
        contact_reason = "call_transfer"
    elif call_under_5s(conv):
        contact_reason = "polyai_bot_not_reached"
    else:
        contact_reason = KB_TOPIC_TO_CONTACT_REASON_MAPPING.get(
            conv.state.matched_topic, "poly_bot_misc"
        )

    conv.write_metric("CONTACT_REASON", contact_reason.upper())
    conv.write_metric("CALL_SUMMARY", conv.state.call_summary)

    # --- Default call_outcome to "hangup" if it was never set ---
    if not conv.state.call_outcome:
        conv.log.info("call_outcome was not set, defaulting to hangup", call_id=conv.id)
        conv.state.call_outcome = "hangup"
