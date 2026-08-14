from _gen import *  # <AUTO GENERATED>
from datetime import datetime
from typing import Optional


from .kb_constants import KB_TOPIC_TO_CONTACT_REASON_MAPPING

CREATE_CALL_SUMMARY_PROMPT = """Your task is to briefly summarize the given call between a caller and a
    virtual assistant. The call_summary will be read by a real human agent after
    the call is transferred to them, and the conversation will continue, so please include what the caller is trying to do or ask for,
    and how the virtual assistant attempted to help them.\n\n

    - The call_summary is an unstructured text field. Keep it brief, using only 1 or 2 sentences that
    concisely describe the purpose of the call.\n\n

    You must immediately call the create_call_summary function to save the call_summary.
    You must also provide a matched_topic parameter, but you can set it to 'DEFAULT' as the topic will be determined automatically.
    Do NOT call any other function.

    You must refrain from including personal identifying information, like the caller's name,
    in the contact summary."""


def get_call_summary_prompt(conv: Conversation):
    prompt = CREATE_CALL_SUMMARY_PROMPT
    if conv.state.call_summary_additional_context:
        prompt += f"\n\nYou must include this additional context in the summary: {conv.state.call_summary_additional_context}"
    return prompt


def _get_matched_topic_from_qa(conv: Conversation) -> Optional[str]:
    """Extract matched topic from QA metrics if available.

    Returns the first QA value that maps to a valid topic, or None if none found.
    """
    try:
        qa_values = [m.value for m in conv.metric_events if "QA" in m.name and m.value]

        if not qa_values:
            return None

        for qa_value in reversed(qa_values):  # Check most recent first
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


def call_under_5s(conv: Conversation):
    time_now = datetime.now()
    if not conv.state.call_start:
        return False
    diff = (time_now - conv.state.call_start).total_seconds()
    if diff < 5:
        return True


@func_description("Summarise the call")
@func_parameter(
    "call_summary",
    "A short, unstructured text field -- limited to 1-3 sentences -- that concisely describes the purpose of the call",
)
@func_parameter(
    "matched_topic",
    "A matched topic on what the call is about from predefined list, or 'DEFAULT' if none of it can be matched",
)
def create_call_summary(conv: Conversation, call_summary: str, matched_topic: str):
    if not conv.state.call_summary_retry_counter:
        conv.state.call_summary_retry_counter = 0
    conv.state.call_summary_retry_counter += 1

    # Get matched topic from QA values/metrics
    matched_topic_from_qa = _get_matched_topic_from_qa(conv)

    if matched_topic_from_qa:
        final_matched_topic = matched_topic_from_qa
        conv.log.info(
            "Using QA value for matched topic",
            qa_topic=matched_topic_from_qa,
            llm_provided_topic=matched_topic,
            call_id=conv.id,
        )
    else:
        final_matched_topic = "DEFAULT"
        conv.log.warning(
            "No QA value found, defaulting to DEFAULT topic",
            llm_provided_topic=matched_topic,
            call_id=conv.id,
        )

    is_verified = conv.state.verified or conv.state.idnv_passed
    verification_status = "VERIFIED USER" if is_verified else "UNVERIFIED USER"

    if call_summary:
        call_summary = f"{verification_status} - {call_summary}"
    else:
        call_summary = verification_status

    conv.state.call_summary = call_summary
    conv.state.matched_topic = final_matched_topic
    conv.log.info(
        "Call summary and matched topic",
        call_summary=conv.state.call_summary,
        matched_topic=conv.state.matched_topic,
        source="qa" if matched_topic_from_qa else "llm",
        call_id=conv.id,
    )

    # Retry if no call_summary provided
    if (
        not conv.state.call_summary
        or (
            conv.state.matched_topic != "DEFAULT"
            and conv.state.matched_topic
            not in KB_TOPIC_TO_CONTACT_REASON_MAPPING.keys()
        )
        and conv.state.call_summary_retry_counter < 2
    ):
        return get_call_summary_prompt(conv)
    elif not conv.state.call_summary:
        conv.state.call_summary = "FAILED TO GENERATE CALL SUMMARY"

    conv.state.summary_added = True

    return_value = conv.state.action_after_call_summary
    if isinstance(return_value, dict) and ("handoff" in return_value.keys()):
        return return_value
