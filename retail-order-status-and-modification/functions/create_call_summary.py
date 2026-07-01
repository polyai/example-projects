from datetime import datetime
from typing import Optional

from _gen import *  # <AUTO GENERATED>

from .kb_constants import KB_TOPIC_TO_CONTACT_REASON_MAPPING
from .zendesk_client import update_custom_fields_on_ticket, update_ticket

nl = "\n"

# CREATE_CALL_SUMMARY_PROMPT = (
#     f"""Your task is to briefly summarize the given call between a caller and a "
#     "virtual assistant and extract two data points: the call_summary, and if relevant, "
#     "a matched topic on what the call is about. The call_summary will be read by a real human agent after "
#     "the call is transferred to them, and the conversation will continue, so please include what the caller is trying to do or ask for, "
#     "and how the virtual assistant attempted to help them.\n\n"

#     "The call_summary is an unstructured text field. Keep it brief, using only 1 or 2 sentences that "
#     "concisely describe the purpose of the call.\n\n"

#     "The matched_topic must come from a predefined list, so please choose the most appropriate "
#     "Option from the following list:\n"
#      {nl.join('- ' + k for k in KB_TOPIC_TO_CONTACT_REASON_MAPPING.keys())}\n"
#     "Here's some additional guidance to help you: "
#     "- This is a partial list of the FAQs retrieved in the conversation: {conv.state.all_qa_values}"
#     "  "
#     "If the conversation cannot be matched to any of the predefined topics, the matched_topic "
#     "can be set to DEFAULT. If the user requested to check their order at any point during the call, "
#     "you must select Orders-track_order as the matched_topic—regardless of whether the item was cancelled or if the caller has questions about a cancelled item.\n\n"

#     "You must immediately call the create_call_summary function to save the call_summary and matched_topic."
#     "Do NOT call any other function.\n\n"

#     "You must refrain from including personal identifying information, like the caller's name, "
#     "in the contact summary."""
# )
# - If the user requested to check their order at any point during the call, you must select Orders-track_order as the matched_topic.
# - If the user wanted to know about REFUNDS at any point during the call, you must select Refunds-track_refund.

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
    # If the user ONLY asked to speak to someone, AND didn't give any other information (i.e., NO other FAQs were retrieved, and NONE of the topics are relevant), the topic should be "General_Behavior-handoff_deflection.
    # - This is a partial list of the FAQs retrieved in the conversation: {conv.state.all_qa_values}

    prompt = CREATE_CALL_SUMMARY_PROMPT
    if conv.state.call_summary_additional_context:
        prompt += f"\n\nYou must include this additional context in the summary: {conv.state.call_summary_additional_context}"
    return prompt


def _get_matched_topic_from_qa(conv: Conversation) -> Optional[str]:
    """
    Extract matched topic from QA metrics if available.
    Returns the first QA value that maps to a valid topic, or None if none found.
    """
    try:
        # Get all QA values from metric events
        qa_values = [m.value for m in conv.metric_events if "QA" in m.name and m.value]

        if not qa_values:
            return None

        # Filter out General_Behavior topics (except handoff_deflection which is valid)
        # and find the first QA value that maps to a valid topic
        for qa_value in reversed(qa_values):  # Check most recent first
            # Skip General_Behavior topics except handoff_deflection
            if (
                qa_value.startswith("General_Behavior")
                and qa_value != "General_Behavior-handoff_deflection"
            ):
                continue

            # Check if this QA value maps to a valid topic
            if qa_value in KB_TOPIC_TO_CONTACT_REASON_MAPPING:
                conv.log.info(
                    "Found matched topic from QA value", qa_value=qa_value, call_id=conv.id
                )
                return qa_value

        conv.log.info(
            "QA values found but none mapped to valid topics", qa_values=qa_values, call_id=conv.id
        )
        return None
    except Exception as e:
        conv.log.error(
            "Error extracting QA values for topic matching", error=str(e), call_id=conv.id
        )
        return None


def call_under_5s(conv: Conversation):
    time_now = datetime.now()
    if not conv.state.call_start:
        return False
    diff = (time_now - conv.state.call_start).total_seconds()
    if diff < 5:
        return True


def update_zendesk_ticket_with_order_details(conv: Conversation):
    comment = {
        "call_reason": conv.state.call_reason,
        "handoff_reason": conv.state.handoff_reason,
        "call_id": conv.id,
        "body": conv.state.call_summary,
        "public": False,
    }

    # if conv.state.handoff_reason in ["ESCALATION"]:
    #     contact_reason = "call_transfer"
    # else:
    #     contact_reason = KB_TOPIC_TO_CONTACT_REASON_MAPPING.get(
    #         conv.state.matched_topic,
    #         "miscellaneous___not_enough_information"
    #         # "polyai_bot_not_reached"
    #     )

    if conv.state.handoff_reason in ["ESCALATION"]:
        contact_reason = "call_transfer"
    elif call_under_5s(conv):
        contact_reason = "polyai_bot_not_reached"
    else:
        contact_reason = KB_TOPIC_TO_CONTACT_REASON_MAPPING.get(
            conv.state.matched_topic, "miscellaneous___not_enough_information"
        )

    if conv.env == "live":
        ticket_field_id = 25278884372503
    else:
        ticket_field_id = 31051749221783

    custom_fields = [
        {"id": ticket_field_id, "value": contact_reason},
    ]

    ticket_status = "open"
    if conv.state.call_outcome == "hangup":
        ticket_status = "solved"
    elif conv.state.call_outcome == "handoff":
        ticket_status = "open"

    if not conv.state.order_details:
        orders = conv.state.orders_from_phone_number or []
        conv.state.order_details = orders[0] if orders else None

    order_details = conv.state.order_details

    order_loyalty_id = getattr(order_details, "loyalty_id", None)
    order_zip = getattr(order_details, "billing_postal_code", None)
    order_first = getattr(order_details, "first_name", None)
    order_last = getattr(order_details, "last_name", None)

    zd_first = getattr(conv.state, "zendesk_first_name", None)
    zd_last = getattr(conv.state, "zendesk_last_name", None)

    is_verified = bool(
        getattr(conv.state, "verified", False) or getattr(conv.state, "idnv_passed", False)
    )

    if is_verified:
        first_name = order_first or zd_first
        last_name = order_last or zd_last
        loyalty_id = order_loyalty_id
        zipcode = order_zip
        conv.log.info(
            "Updating Zendesk ticket with VERIFIED user details",
            verified=is_verified,
            ticket_id=conv.state.zendesk_ticket_id,
            first_name=first_name,
            last_name=last_name,
            loyalty_number=loyalty_id,
            postal_code=zipcode,
        )
    else:
        first_name = zd_first
        last_name = zd_last
        loyalty_id = None
        zipcode = None
        conv.log.info(
            "Updating Zendesk ticket with UNVERIFIED user details (names only)",
            verified=is_verified,
            ticket_id=conv.state.zendesk_ticket_id,
            first_name=first_name,
            last_name=last_name,
        )

    update_ticket(
        conv=conv,
        ticket_id=conv.state.zendesk_ticket_id,
        ticket_status=ticket_status,
        comment=comment,
        custom_fields=custom_fields,
    )
    conv.state.summary_added = True

    if not conv.state.ticket_details_updated:
        update_custom_fields_on_ticket(
            conv,
            first_name=first_name,
            last_name=last_name,
            loyalty_number=loyalty_id,
            postal_code=zipcode,
        )
        conv.state.ticket_details_updated = True


@func_description("Summarise the call")
@func_parameter(
    "call_summary",
    "A short, unstructured text field—limited to 1-3 sentences—that concisely describes the purpose of the call",
)
@func_parameter(
    "matched_topic",
    "A matched topic on what the call is about from predefined list, or 'DEFAULT' if none of it can be matched",
)
def create_call_summary(conv: Conversation, call_summary: str, matched_topic: str):
    if not conv.state.call_summary_retry_counter:
        conv.state.call_summary_retry_counter = 0
    conv.state.call_summary_retry_counter += 1

    # Get matched topic from QA values/metrics (the "dictionary")
    # LLM-provided topic is ignored since we always use QA values or DEFAULT
    matched_topic_from_qa = _get_matched_topic_from_qa(conv)

    if matched_topic_from_qa:
        final_matched_topic = matched_topic_from_qa
        conv.log.info(
            "Using QA value for matched topic",
            qa_topic=matched_topic_from_qa,
            llm_provided_topic=matched_topic,  # Logged for debugging but not used
            call_id=conv.id,
        )
    else:
        final_matched_topic = "DEFAULT"
        conv.log.warning(
            "No QA value found, defaulting to DEFAULT topic",
            llm_provided_topic=matched_topic,  # Logged for debugging but not used
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

    # retry if no call_summary provided
    if (
        not conv.state.call_summary
        or (
            conv.state.matched_topic != "DEFAULT"
            and conv.state.matched_topic not in KB_TOPIC_TO_CONTACT_REASON_MAPPING.keys()
        )
        and conv.state.call_summary_retry_counter < 2
    ):
        return get_call_summary_prompt(conv)
    elif not conv.state.call_summary:
        conv.state.call_summary = "FAILED TO GENERATE CALL SUMMARY"

    update_zendesk_ticket_with_order_details(conv)

    return_value = conv.state.action_after_call_summary
    if isinstance(return_value, dict) and ("handoff" in return_value.keys()):
        return return_value
