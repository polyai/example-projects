import re

from _gen import *  # <AUTO GENERATED>
from functions.real_time_handoff_config import (
    get_out_of_scope_post_faq_deflections,
    get_out_of_scope_pre_faq_deflections,
)

# Matching patterns for each intent category, derived from the Poly Bank knowledge base.
# Order matters: THREAT_TO_LIFE is first so it is checked before disambiguation.
INTENT_PATTERNS = {
    "THREAT_TO_LIFE": [
        r"\bemotionally drained\b",
        r"\bdark thoughts\b",
        r"\bdon't see a future\b",
        r"\bcut myself\b",
        r"\bend my life\b",
        r"\bending it all\b",
        r"\bend it all\b",
        r"\blost everything\b",
        r"\blosing everything\b",
        r"\blost it all\b",
        r"\blosing it all\b",
        r"\blost control\b",
        r"\blose control\b",
        r"\blosing control\b",
        r"\bcan't survive\b",
        r"\bcannot survive\b",
        r"\bcan't cope\b",
        r"\bcannot cope\b",
        r"\bdestroyed me\b",
        r"\bdestroying me\b",
        r"\bruined me\b",
        r"\bruined my\b",
        r"\bempty inside\b",
        r"\bdone fighting\b",
        r"\bweight of it all\b",
        r"\bfinal warning\b",
        r"\bfinal message\b",
        r"\bno future\b",
        r"\bi'm broken\b",
        r"\bbroke me\b",
        r"\bdebt trap\b",
        r"\bsuicidal\b",
        r"\bsuicide\b",
        r"\bdangerous\b",
        r"\bdanger\b",
        r"\bunstable\b",
        r"\bworthless\b",
        r"\bunwanted\b",
        r"\bunloved\b",
        r"\bdie\b",
        r"\bdies\b",
        r"\bsafety\b",
        r"\brisk\b",
        r"\bharm\b",
        r"\bhurt\b",
        r"\bhurting\b",
        r"\bkill\b",
    ],
    "CARDS": [
        r"\bcard\b",
        r"\bcards\b",
        r"\bdebit\s*card\b",
        r"\bcredit\s*card\b",
        r"\bcontactless\b",
        r"\bapple\s*pay\b",
        r"\bgoogle\s*pay\b",
        r"\bpin\b",
        r"\bactivat\w*\s*(my\s*)?card\b",
        r"\bcard\s*activat\w*\b",
        r"\bblock\w*\s*(my\s*)?card\b",
        r"\bcard\s*block\w*\b",
        r"\bfreez\w*\s*(my\s*)?card\b",
        r"\bcard\s*freez\w*\b",
        r"\blost\s*(my\s*)?card\b",
        r"\bcard\s*lost\b",
        r"\bstolen\s*(my\s*)?card\b",
        r"\bcard\s*stolen\b",
        r"\bdeclin\w*\b",
        r"\bcard\s*not\s*work\w*\b",
        r"\bcard\s*disput\w*\b",
        r"\bcard\s*swallow\w*\b",
        r"\bcard\s*replacement\b",
        r"\breplace\w*\s*(my\s*)?card\b",
        r"\bwithdraw\w*\b",
        r"\batm\b",
        r"\bchargeback\b",
        r"\bvisa\b",
        r"\bmastercard\b",
        r"\bunblock\w*\s*(my\s*)?card\b",
        r"\bcard\s*unblock\w*\b",
    ],
    "PAYMENTS": [
        r"\bpayment\w*\b",
        r"\bpay\s+(?!attention|day|rise)\w*\b",
        r"\btransfer\b",
        r"\bsend\s*money\b",
        r"\bfaster\s*payment\w*\b",
        r"\binternational\s*payment\w*\b",
        r"\bstanding\s*order\b",
        r"\bdirect\s*debit\b",
        r"\bcancel\w*\s*(a\s*)?(payment|direct\s*debit|standing\s*order)\b",
        r"\biban\b",
        r"\bbic\b",
        r"\bswift\b",
        r"\brefund\b",
        r"\bpending\s*transaction\b",
        r"\bduplicate\s*payment\b",
        r"\bmissed\s*payment\b",
        r"\bpayment\s*not\s*arriv\w*\b",
        r"\bbulk\s*payment\b",
        r"\bpayment\s*revers\w*\b",
        r"\bnew\s*beneficiar\w*\b",
        r"\bnew\s*payee\b",
        r"\bdelete\s*payee\b",
    ],
    "APP_OR_ONLINE_BANKING": [
        r"\bapp\b",
        r"\bmobile\s*(?:banking\s*)?app\b",
        r"\bonline\s*banking\b",
        r"\binternet\s*banking\b",
        r"\bexample-bank\b",
        r"\blog\s*(?:in|out)\b",
        r"\blogin\b",
        r"\bpassword\b",
        r"\bregister\w*\s*(?:for\s*)?(?:online|mobile|internet|app)?\s*banking\b",
        r"\bderegister\w*\b",
        r"\bdevice\b",
        r"\bcustomer\s*number\b",
        r"\bmagic\s*word\b",
        r"\bapp\s*not\s*work\w*\b",
        r"\bcan'?t\s*(?:log|access|sign)\b",
        r"\breset\s*(?:my\s*)?(?:password|pin|counter)\b",
        r"\bmobile\s*app\s*registr\w*\b",
    ],
    "ACCOUNTS": [
        r"\baccount\w*\b",
        r"\bcurrent\s*account\b",
        r"\bsavings?\b",
        r"\bsavings?\s*account\b",
        r"\bbalance\b",
        r"\bstatement\w*\b",
        r"\bopen\w*\s*(?:an?\s*)?account\b",
        r"\bclose\w*\s*(?:my\s*)?account\b",
        r"\bswitch\w*\s*(?:my\s*)?account\b",
        r"\bdormant\b",
        r"\boverdraft\b",
        r"\bisa\b",
        r"\bfixed\s*term\b",
        r"\blimited\s*edition\s*savings\b",
        r"\bsavings?\s*account\s*info\b",
        r"\bopen\w*\s*savings\b",
        r"\bdocs?\s*to\s*open\b",
    ],
}


# def _get_first_match(user_query: str, patterns: list) -> str | None:
#   """Return the first substring matched by any pattern, or None."""
#  for pattern in patterns:
#       m = re.search(pattern, user_query, re.IGNORECASE)
#      if m:
#         return m.group(0)
#  return None


def _oos_handoff_offer_response():
    return {
        "utterance": "Ok, I'd be happy to put you through to one of our team members who can help with this. Does that sound alright?",
        "content": "If the user accepts, call the handoff function with reason='OUT_OF_SCOPE'. If they decline, ask what else you can help with.",
    }


def _is_affirmative_response(user_query: str) -> bool:
    text = (user_query or "").strip().lower()
    if not text:
        return False
    return bool(
        re.search(
            r"\b(yes|yeah|yep|ok|okay|sure|please do|go ahead|that's fine|that is fine|alright|sounds good|do it)\b",
            text,
            re.IGNORECASE,
        )
    )


def _is_negative_response(user_query: str) -> bool:
    text = (user_query or "").strip().lower()
    if not text:
        return False
    return bool(
        re.search(
            r"\b(no|nope|nah|don't|do not|not now|no thanks|no thank you|that's all|that is all)\b",
            text,
            re.IGNORECASE,
        )
    )


def _disambiguation_utterance_for_intent(detected_intent):
    if detected_intent == "CARDS":
        return {
            "utterance": "Ok, it sounds like you've got a question about cards. I can help with activating a card, reporting a lost or stolen card, a declined payment, Apple Pay, or card disputes. Could you tell me a bit more about what you need?"
        }
    if detected_intent == "PAYMENTS":
        return {
            "utterance": "Ok, I understand you've got a question about payments. I can help with making a payment, a payment that hasn't arrived, standing orders, direct debits, or international transfers. What specifically can I help you with?"
        }
    if detected_intent == "APP_OR_ONLINE_BANKING":
        return {
            "utterance": "Ok, I understand you've got a question about online or mobile banking. I can help with logging in, the app not working, registering for online or mobile banking, or deregistering a device. What is it you're looking for?"
        }
    if detected_intent == "ACCOUNTS":
        return {
            "utterance": "Ok, I understand you've got a question about your account. I can tell you about current accounts, savings accounts, opening or closing an account, or statements. What would you like to know?"
        }
    return {
        "utterance": "I'm not sure I fully caught that, could you tell me exactly what you need help with?"
    }


def detect_intent_keyword(user_query: str):
    """
    Detects the intent category from the user query using pattern matching.
    Returns the matched intent category string, or None if no match is found.
    """
    query_lower = user_query.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return intent
    return None


@func_description(
    "Call this function immediately, without saying anything, whenever the user asks a question you don't understand or have no relevant information for, to run an intent check and provide appropriate disambiguation. Call even if you called it last turn."
)
@func_parameter("user_query", "The full transcript of the latest user message to check for intent")
@func_parameter(
    "query_topic",
    "The topic of the user's query in one word or a short phrase, or 'unclear' if the input is unintelligible, or the faq_id of the topic you were using if the user asked an out of scope follow up question about a response you just gave.",
)
def OUT_OF_SCOPE_CHECK(conv: Conversation, user_query: str, query_topic: str):
    detected_intent = detect_intent_keyword(user_query)
    qa_in_history = any(m.name == "QA" for m in reversed(conv.metric_events))
    last_qa_metric = None
    if qa_in_history:
        last_qa_metric = next(
            (m.value for m in reversed(conv.metric_events) if m.name == "QA"), None
        )
    # THREAT_TO_LIFE: hand off immediately (no disambiguation)
    if detected_intent == "THREAT_TO_LIFE":
        return {
            "content": "Call the handoff function immediately with reason='THREAT_TO_LIFE'. Do not say anything else first."
        }

    if not qa_in_history:
        # If transfer offer is already active, interpret yes/no and avoid re-entering deflection loop.
        if getattr(conv.state, "OOS_PRE_FAQ_OFFERED", False):
            if _is_affirmative_response(user_query):
                return {
                    "content": "Call the handoff function immediately with reason='OUT_OF_SCOPE'."
                }
            if _is_negative_response(user_query):
                conv.state.OOS_PRE_FAQ_OFFERED = False
                conv.state.OOS_CHECK_REPEATS = 0
                return {"utterance": "No problem. Is there anything else I can help with?"}
            return _oos_handoff_offer_response()

        if not conv.state.OOS_CHECK_REPEATS:
            conv.state.OOS_CHECK_REPEATS = 0

        pre_limit = get_out_of_scope_pre_faq_deflections(conv)
        if conv.state.OOS_CHECK_REPEATS < pre_limit:
            conv.state.OOS_CHECK_REPEATS += 1
            conv.write_metric("MISSING_TOPIC", query_topic)
            return _disambiguation_utterance_for_intent(detected_intent)
        conv.state.OOS_PRE_FAQ_OFFERED = True
        return _oos_handoff_offer_response()

    if qa_in_history:
        conv.state.OOS_PRE_FAQ_OFFERED = False
        conv.state.OOS_CHECK_REPEATS = 0
        if query_topic == last_qa_metric:
            conv.state.OOS_POST_FAQ_OFFERED = False
            conv.state.OOS_CHECK_REPEATS_POST_QA = 0
            return {
                "content": f"Provide the same information you gave the user last time about '{last_qa_metric}' and add: 'If you need more information about this, the fastest way would be to visit our website and search for it there. Is there anything else I can help you with?'"
            }
        else:
            if getattr(conv.state, "OOS_POST_FAQ_OFFERED", False):
                if _is_affirmative_response(user_query):
                    return {
                        "content": "Call the handoff function immediately with reason='OUT_OF_SCOPE'."
                    }
                if _is_negative_response(user_query):
                    conv.state.OOS_POST_FAQ_OFFERED = False
                    conv.state.OOS_CHECK_REPEATS_POST_QA = 0
                    return {"utterance": "No problem. Is there anything else I can help with?"}
                return _oos_handoff_offer_response()
            if not conv.state.OOS_CHECK_REPEATS_POST_QA:
                conv.state.OOS_CHECK_REPEATS_POST_QA = 0
            conv.state.OOS_CHECK_REPEATS_POST_QA += 1
            conv.write_metric("MISSING_TOPIC", query_topic)

            post_limit = get_out_of_scope_post_faq_deflections(conv)
            if conv.state.OOS_CHECK_REPEATS_POST_QA <= post_limit:
                return _disambiguation_utterance_for_intent(detected_intent)
            conv.state.OOS_POST_FAQ_OFFERED = True
            return _oos_handoff_offer_response()
