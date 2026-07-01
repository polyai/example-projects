import re
from collections import defaultdict

from _gen import *  # <AUTO GENERATED>
from functions.utterances import utterance


def extract_and_group_items(text):
    # Remove intro phrase

    text = re.sub(r"^(The item is |The items are )", "", text, flags=re.IGNORECASE)

    # Regex pattern for item name + URL
    pattern = re.compile(r"(.*?)\s+in\s+.*?\s+category\..*?(https?://\S+)", re.IGNORECASE)

    groups = defaultdict(list)

    for match in pattern.finditer(text):
        name, url = match.groups()

        groups[url.strip()].append(name.strip())

    # Format results
    results = []
    for url, items in groups.items():
        item_list = "; ".join(items)
        results.append(f"{item_list}: {url}")

    return results


def is_valid_US_number(phone_number: str):
    """
    Validates if a phone_number is a valid US number
    """
    if not phone_number:
        return False
    # Regex pattern to match US numbers
    pattern = r"^(?:\+1|1)?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$"

    is_match = re.match(pattern, phone_number)
    return is_match


@func_description("Start sending the user the tracking link.")
def start_sending_narvar_link(conv: Conversation, flow: Flow):
    print(type(conv.state.product_description))

    conv.state.item_urls = extract_and_group_items(conv.state.product_description)

    print(conv.state.item_urls)

    if not conv.state.item_urls:
        return {
            "content": "I wasn't able to find a tracking link for your order, but you can check your email for tracking updates. Is there anything else I can help you with?",
            "transition": {
                "goto_flow": "OMS_WISMO",
                "goto_step": "Determine what user needs next",
            },
        }

    conv.state.coming_from_WISMO = True

    # set initial sms value
    conv.state.tracking_sms = conv.state.item_urls.pop()

    conv.state.sms_id = "Narvar tracking link"
    conv.write_metric("SMS_OFFERED", write_once=True)
    conv.write_metric("SMS_ACCEPTED")
    conv.write_metric("SMS_ID", conv.state.sms_id)
    conv.state.sms_content = None
    conv.state.readback_occurred = False

    if conv.state.sent_sms_to_number:
        return {
            "transition": {
                "goto_flow": "SMS flow",
                "goto_step": "Send SMS",
            }
        }
    # if a valid US number, check user wants text sent to their number
    elif is_valid_US_number(conv.state.caller_number_cleanedup):
        return {
            "utterance": utterance(conv, "sms_ask_this_number"),
            "transition": {
                "goto_flow": "SMS flow",
                "goto_step": "Ask this number",
            },
        }
    # if not a valid US number, go straight to collection step
    else:
        return {
            "utterance": utterance(conv, "sms_ask_number"),
            "transition": {
                "goto_flow": "SMS flow",
                "goto_step": "Phone number collected",
            },
        }
