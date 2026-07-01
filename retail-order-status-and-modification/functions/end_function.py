import json
import re
from typing import Optional

from _gen import *  # <AUTO GENERATED>

from .create_call_summary import call_under_5s
from .kb_constants import KB_TOPIC_TO_CONTACT_REASON_MAPPING
from .zendesk_client import update_custom_fields_on_ticket, update_ticket

# KB_TOPIC_TO_CONTACT_REASON_MAPPING = {
#   'Corporate-delete_account': 'corporate__data_deletion',
#   'Delivery_Issues-damaged_parcel': 'delivery_issues__damaged_package_or_product',
#   'Delivery_Issues-missing_item': 'delivery_issues__missing_item',
#   'Delivery_Issues-wrong_item_received': 'delivery_issues__wrong_item',
#   'Discount_Codes-not_working': 'discounts_and_promos__discount_not_working/expired',
#   'Gift_Cards-check_balance': 'payment__gift_card_issues__balance_inquiry',
#   'Gift_Cards-email_not_received': 'payment__gift_card_issues__not_received',
#   'Gift_Cards-issues_with_pin': 'payment__gift_card_issues__gc_fraud/pin_issues',
#   'Instore-opening_hours': 'store_related__store_hours',
#   'Instore-order_pickup': 'store_related__pickup_inquiry',
#   'Instore-order_pickup_how_long_hold': 'store_related__pickup_inquiry',
#   'Instore-order_pickup_when_ready': 'store_related__pickup_inquiry',
#   'Instore-product_issues': 'store_related__issue_with_product_purchased_in_store',
#   'Orders-canceled_by_FL-payment_issue': 'orders__question_about_cancellation-payment',
#   'Orders-canceled_by_FL-product_not_available': 'orders__question_about_cancellation-product',
#   'Orders-change_or_cancel': 'orders__request_cancellation',
#   'Orders-email_not_received': 'orders__missing_email_confirmation',
#   'Orders-tracking_number_not_working': 'orders__tracking_information',
#   'Product-information': 'product__product_informations',
#   'Product-launches': 'product__product_launchess',
#   'Product-out_of_stock': 'product__product_availabilitys',
#   'Refunds-refund_after_cancellation': 'payment__question_about_cancellation_-_payment',
#   'Refunds-track_refund': 'delivery_issues__status_of_claim_or_refund',
#   'Returns-return_policy': 'returns_and_refunds__return_policy',
#   'Returns-shipping_time': 'returns_and_refunds__return_status',
#   'Returns-start_a_return': 'returns_and_refunds__return_instructions',
#   'Returns-track_exchange': 'returns_and_refunds__exchange_status',
#   'Shipping-free_shipping': 'discounts_and_promos__item_exclusion',
#   'Shipping-shipping_costs': 'shipping_options__shipping_cost',
#   'Shipping-shipping_time': 'shipping_options__shipping_timeframe',
#   'Technical_Issues-create_account': 'technical_issues__questions_about_my_account',
#   'Technical_Issues-log_in': 'technical_issues__log_in_issue',
#   'Technical_Issues-update_info': 'technical_issues__questions_about_my_account',
#   'Technical_Issues-website_issues': 'technical_issues__website_issue',
#   'Orders-track_order': 'orders__tracking_information',
# }
HANGUP_CALL_SUMMARY_PROMPT = (
    "Your task is to briefly summarize the given call between a caller and a "
    "virtual assistant. The call_summary will be read by a real human agent after the call, "
    "so please include what the caller is trying to do or ask for, and how the virtual assistant "
    "attempted to help them.\n\n"
    "The output must be valid JSON with exactly this key:\n"
    "{\n"
    '  "call_summary": "<1–2 sentence summary>"\n'
    "}\n\n"
    "The call_summary should be brief, using only 1 or 2 sentences that concisely describe the purpose of the call, "
    "and must not contain any personal identifying information (such as the caller's name)."
)
# HANGUP_CALL_SUMMARY_PROMPT = (
#     f"""Your task is to briefly summarize the given call between a caller and a
#     virtual assistant and extract two data points: the call_summary, and a matched_topic on what the call is about.
#     The call_summary will be read by a real human agent after the call, so please include what the caller is trying
#     to do or ask for, and how the virtual assistant attempted to help them.\n\n"

#     The output must be valid JSON with exactly these two keys:\n
#     {{\n
#       "call_summary": "<1–2 sentence summary>",\n
#       "matched_topic": "<topic or DEFAULT>"\n
#     }}\n\n

#     The call_summary should be brief, using only 1 or 2 sentences that concisely describe the purpose of the call,
#     and must not contain any personal identifying information (such as the caller's name).\n\n

#     The matched_topic must come from the following predefined list:\n
#     {chr(10).join('- ' + k for k in KB_TOPIC_TO_CONTACT_REASON_MAPPING.keys())}\n\n
#     Here's some additional guidance to help you determine the matched topic:
#     - If the user ONLY asked to speak to someone, and didn't give ANY other information (i.e., NONE of the topics are relevant), the topic should be 'General_Behavior-handoff_deflection'.
#     - If the user asked about a specific topic, the topic that best fits the user's query should be used - EVEN IF they ALSO asked to speak to an agent.
#     - If the user asked about changing their address, select Orders-change_or_cancel.
#     - If the user requested to check their order at any point during the call, you must select Orders-track_order as the matched_topic.
#     - If the user wanted to know about REFUNDS at any point during the call, you must select Refunds-track_refund.
#     - If the conversation cannot be matched to any of the predefined topics, the matched_topic can be set to DEFAULT."""
# )


def _extract_json_from_text(text: str) -> str:
    if not text:
        return text
    s = text.strip()

    # Strip fenced code blocks: ```json ... ``` or ``` ... ```
    m = re.search(r"```(?:json)?\s*(.+?)\s*```", s, flags=re.DOTALL | re.IGNORECASE)
    if m:
        s = m.group(1).strip()

    # If it doesn't start with '{', try a simple slice between first '{' and last '}'
    if not s.lstrip().startswith("{"):
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            s = s[start : end + 1].strip()

    return s


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


def end_function(conv: Conversation):
    if not conv.state.summary_added:
        # First, try to get matched topic from QA values/metrics (the "dictionary")
        matched_topic_from_qa = _get_matched_topic_from_qa(conv)

        # Try LLM to get call summary (and matched topic as fallback if no QA value)
        summary_text = ""
        matched_topic = None
        llm_failed = False
        llm_call_failed = False
        raw_response = None

        conv.log.info(
            "Attempting LLM call for hangup summary",
            has_qa_topic=bool(matched_topic_from_qa),
            qa_topic=matched_topic_from_qa,
        )

        try:
            raw_response = conv.utils.prompt_llm(HANGUP_CALL_SUMMARY_PROMPT, show_history=True)
            conv.log.info(
                "LLM call completed successfully",
                raw_response_length=len(raw_response) if raw_response else 0,
                raw_response_preview=raw_response[:200] if raw_response else None,
            )

            safe_json = _extract_json_from_text(raw_response)
            parsed = json.loads(safe_json)
            summary_text = parsed.get("call_summary", "").strip()

            conv.log.info("Successfully parsed LLM response", has_summary=bool(summary_text))

            # Use QA value for topic, or DEFAULT if no QA value found
            if matched_topic_from_qa:
                matched_topic = matched_topic_from_qa
                conv.log.info("Using QA value for matched topic", qa_topic=matched_topic_from_qa)
            else:
                matched_topic = "DEFAULT"
                conv.log.warning("No QA value found, defaulting to DEFAULT topic")
        except json.JSONDecodeError as e:
            llm_failed = True
            conv.log.error(
                "Failed to parse LLM hangup summary JSON",
                raw_response=raw_response,
                raw_response_length=len(raw_response) if raw_response else 0,
                error=str(e),
                error_type="JSONDecodeError",
            )
            # If LLM failed, use QA value if available
            if matched_topic_from_qa:
                matched_topic = matched_topic_from_qa
                conv.log.info(
                    "LLM JSON parsing failed, using QA value as fallback",
                    qa_topic=matched_topic_from_qa,
                )
            else:
                matched_topic = "DEFAULT"
                conv.log.warning(
                    "LLM JSON parsing failed and no QA value found, defaulting to DEFAULT"
                )
        except Exception as e:
            llm_failed = True
            llm_call_failed = True
            conv.log.error(
                "LLM call or processing failed",
                raw_response=raw_response,
                raw_response_length=len(raw_response) if raw_response else 0,
                error=str(e),
                error_type=type(e).__name__,
                call_id=conv.id,
            )
            # If LLM failed, use QA value if available
            if matched_topic_from_qa:
                matched_topic = matched_topic_from_qa
                conv.log.info(
                    "LLM call failed, using QA value as fallback",
                    qa_topic=matched_topic_from_qa,
                    call_id=conv.id,
                )
            else:
                matched_topic = "DEFAULT"
                conv.log.warning(
                    "LLM call failed and no QA value found, defaulting to DEFAULT", call_id=conv.id
                )

        # Final fallback: if we still don't have a valid topic, use DEFAULT
        if not matched_topic:
            matched_topic = matched_topic_from_qa or "DEFAULT"

        is_verified = bool(conv.state.verified or conv.state.idnv_passed)
        prefix = "VERIFIED USER" if is_verified else "UNVERIFIED USER"

        conv.state.call_summary = f"{prefix} - {summary_text}" if summary_text else prefix
        conv.state.matched_topic = matched_topic

        conv.log.info(
            "Set matched topic and call summary",
            matched_topic=matched_topic,
            call_summary=conv.state.call_summary,
            source="qa"
            if matched_topic_from_qa and matched_topic == matched_topic_from_qa
            else "llm"
            if not llm_failed
            else "fallback",
            llm_failed=llm_failed,
            llm_call_failed=llm_call_failed,
            call_id=conv.id,
        )
    else:
        # Log when we're NOT processing hangup summary (for debugging)
        conv.log.info(
            "Skipping hangup summary processing",
            call_outcome=conv.state.call_outcome,
            summary_added=conv.state.summary_added,
            call_id=conv.id,
        )

    # Check whether we offered SMS
    for turn in conv.history:
        if turn.role == "agent" and re.search(
            r"\b(?:would you like me to (?:send you|text you)|i(?:'ll| will) (?:send|text)|can send you|can text you|could you.*(?:send|text)|if you'd like, i can (?:send|text))\b.*?\b(?:sms|text)\b",
            turn.text,
            flags=re.IGNORECASE,
        ):
            conv.write_metric("SMS_OFFERED", write_once=True)

    comment = {
        "call_reason": conv.state.call_reason,
        "handoff_reason": conv.state.handoff_reason,
        "call_id": conv.id,
        "body": conv.state.call_summary,
        "public": False,
    }

    # if conv.state.handoff_reason in ["ESCALATION"]:
    #   contact_reason = 'call_transfer'
    # else:
    #   contact_reason = KB_TOPIC_TO_CONTACT_REASON_MAPPING.get(
    #     conv.state.matched_topic,
    #     # "polyai_bot_not_reached"
    #     "miscellaneous___not_enough_information"

    #   )
    if conv.state.handoff_reason in ["ESCALATION"]:
        contact_reason = "call_transfer"
    elif call_under_5s(conv):
        contact_reason = "polyai_bot_not_reached"
    else:
        contact_reason = KB_TOPIC_TO_CONTACT_REASON_MAPPING.get(
            conv.state.matched_topic, "poly_bot_misc"
        )

    if conv.env == "live":
        ticket_field_id = 25278884372503
    else:
        ticket_field_id = 31051749221783

    custom_fields = [
        {"id": ticket_field_id, "value": contact_reason},
    ]

    conv.write_metric("CONTACT_REASON", contact_reason.upper())
    conv.write_metric("CALL_SUMMARY", conv.state.call_summary)

    # Default call_outcome to "hangup" if it was never set.
    # If we're in end_function without call_outcome == "handoff" (set by transfer_call),
    # then the call was not handed off — the caller hung up or the bot ended the call
    # via a path that didn't go through end_call (e.g. user dropped mid-call,
    # silence_hangup, handle_wait_and_silence, etc.).
    if not conv.state.call_outcome:
        conv.log.info(
            "call_outcome was not set, defaulting to hangup",
            call_id=conv.id,
        )
        conv.state.call_outcome = "hangup"

    # Determine the ticket status based on the agent call outcome
    ticket_status = "open"  # Make it open by default
    if conv.state.call_outcome == "hangup":
        ticket_status = "solved"
    elif conv.state.call_outcome == "handoff":
        ticket_status = "open"

    if not conv.state.order_details:
        orders = conv.state.orders_from_phone_number or []
        conv.state.order_details = orders[0] if orders else None

    print(conv.state.order_details)

    order_details = conv.state.order_details

    order_loyalty_id = order_details.loyalty_id if order_details else None
    order_zip = order_details.billing_postal_code if order_details else None
    order_first = order_details.first_name if order_details else None
    order_last = order_details.last_name if order_details else None

    zd_first = conv.state.zendesk_first_name
    zd_last = conv.state.zendesk_last_name

    is_verified = bool(conv.state.verified or conv.state.idnv_passed)

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

    print(comment)

    if not conv.state.summary_added:
        update_ticket(
            conv=conv,
            ticket_id=conv.state.zendesk_ticket_id,
            ticket_status=ticket_status,
            comment=comment,
            custom_fields=custom_fields,
        )

    if not conv.state.ticket_details_updated:
        update_custom_fields_on_ticket(
            conv,
            first_name=first_name,
            last_name=last_name,
            loyalty_number=loyalty_id,
            postal_code=zipcode,
        )
