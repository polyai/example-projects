import re
from typing import Optional

import boto3
from _gen import *  # <AUTO GENERATED>
from botocore.exceptions import ClientError, NoCredentialsError
from functions.vc_keywords import VC_KEYWORDS

# Only handoff reasons with non-default utterances
HANDOFF_REASON_TO_UTTERANCE = {
    "ACCOUNT_BLOCKED_SPEAK_TO": "I'll put you through to our team right away to help with your blocked or frozen account. Please hold the line for one moment.",
    "OTHER_ACCOUNT_PROBLEMS": "I'll put you through to our team right away to help with your account problems. Please hold the line for one moment.",
    "APP_NOT_WORKING_NEW_MAGIC_WORD": "Ok, if you've forgotten both your password and security number, you'll need to speak to our team to get your Magic Word reissued. I'll put you through now.",
    "APPLE_PAY": "I'll put you through to our team who can help with that. Please hold the line for one moment.",
    "BALANCE_REQUEST": "I'll transfer you to someone who can help with your balance query. Please hold the line for one moment.",
    "BLOCK_USERS_CARD": "I'll put you through to our team who can help block someone else's card. Please hold the line for one moment.",
    "BULK_PAYMENTS_BUSINESS": "I'll put you through to our business team who can help with bulk payments. Please hold the line for one moment.",
    "BULK_PAYMENTS_DOMESTIC": "I'll put you through to our team who can help with domestic bulk payments. Please hold the line for one moment.",
    "BULK_PAYMENTS_INTERNATIONAL": "I'll put you through to our team who can help with international bulk payments. Please hold the line for one moment.",
    "BUSINESS_BBLS_EXISTING": "I'll transfer you to someone who can help with your existing loan. Please hold the line for one moment.",
    "CANCEL_LOST_STOLEN_CARD": "I'll transfer you to someone who can help cancel your card immediately. Please hold the line for one moment.",
    "CLOSEST_STORE": "I'll put you through to someone who can help you find your nearest branch. Please hold the line for one moment.",
    "CLOSE_ACCOUNT": "I'll transfer you to someone who can help close your account. Please hold the line for one moment.",
    "CREDIT_CARD_APPLY": "I'll transfer you to someone who can help with your application. Please hold the line for one moment.",
    "FORGOT_CUSTOMER_NUMBER": "Let me put you through to someone who can help you find your customer number. Please hold the line for one moment.",
    "BEREAVEMENT": "[compassionate] I'm sorry to hear about your loss. [compassionate] Our team are here to help. [compassionate] Let me put you through to someone else, one moment please.",
    "VC_KEYWORD_TRANSFER": "[compassionate] I'll put you through to our team who can give you the support you need. Please hold the line for one moment.",
}

DEFAULT_HANDOFF_UTTERANCE = (
    "I'll transfer you to someone who can help. Please hold the line for one moment."
)


def get_vc_keyword_match(text: str) -> Optional[str]:
    """
    Returns the first VC keyword found in text (word-boundary match), or None.
    Used to trigger immediate transfer and to log which keyword triggered.
    """
    if not text or not text.strip():
        return None
    pattern = r"\b(" + "|".join(re.escape(k) for k in VC_KEYWORDS) + r")\b"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def handoff_reason_to_utterance(conv: Conversation, reason: str):
    utterance = HANDOFF_REASON_TO_UTTERANCE.get(reason)

    if not utterance:
        utterance = DEFAULT_HANDOFF_UTTERANCE

    return utterance


def number_in_vc_table(
    conv: Conversation,
    caller_number: str,
    table_name="poly-bank-handoff-config",
    region="us-east-1",
):
    """
    Looks up ANI from DynamoDB table
    """

    if not caller_number:
        return False
    number = re.sub(r"[\s()+-]", "", caller_number)
    try:
        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)

        response = table.get_item(Key={"phone_number": number})

        if "Item" in response:
            conv.log.info("Identified ANI", number=number)
            return True
        else:
            conv.log.info(f"Number {number} not found in database")
            return False

    except NoCredentialsError:
        conv.log.warning(
            "AWS credentials not found — falling back to mock VC check",
            number=number,
        )
        try:
            from functions.mock_api import MockVulnerableCustomerCheck

            return MockVulnerableCustomerCheck.is_vulnerable(number)
        except ImportError:
            conv.log.error("Mock API not available for VC fallback")
            return False
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            conv.log.error(f"Table {table_name} not found when attempting ANI lookup")
        else:
            conv.log.error("DynamoDB Error", error=e)
        return False
    except Exception as e:
        conv.log.error("Unexpected error when attempting ANI lookup", error=e)
        return False


def is_vulnerable_customer(conv: Conversation):
    caller_number = conv.caller_number
    # if conv.env in {'draft', 'sandbox'}:
    # TEST NUMBER in VC DDB
    # caller_number = "+447736126554"
    flags = conv.real_time_config.get("flags", {})
    if not flags:
        return False
    vc_handoff_enabled = flags.get("vc_handoff_enabled", False)
    print(f"Caller Number: {caller_number}")
    print(f"Vulnerable Customer Check Enabled: {vc_handoff_enabled}")
    if not vc_handoff_enabled or not caller_number:
        return False
    conv.log.info(f"Making DDB request for {caller_number}")
    return number_in_vc_table(conv, caller_number)


@func_description("[UTIL] Handoff utils")
def handoff_utils(conv: Conversation):
    pass
