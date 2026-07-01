from _gen import *  # <AUTO GENERATED>

INTENT_TO_ROUTE = {
    "GENERAL_QUESTION": "CUSTOMER_CARE",
    "COMPLAINT": "CUSTOMER_CARE",
    "MAKE_APPOINTMENT": "CUSTOMER_CARE",
    "CONFIRM_APPOINTMENT": "CUSTOMER_CARE",
    "MODIFY_APPOINTMENT": "CUSTOMER_CARE",
    "CANCEL_APPOINTMENT": "ACCOUNT_CARE",
    "BILLING_QUESTION": "BILLING",
    "CANCEL_SUBSCRIPTION": "ACCOUNT_CARE",
    "INSPECTION_REQUEST": "NS_SCHEDULING_INBOUND",
    "NEW_SALE": "INSIDE_SALES",
    "COMMERCIAL_SERVICE": "COMMERCIAL",
    "CALL_BACK": "CUSTOMER_CARE",
    "WELCOME_CALL": "WELCOME_CALL",
    "SPANISH": "SPANISH",
}


@func_description(
    "During business hours, call this function to route the caller to the correct queue. Do NOT say anything else — just call this function with the caller's intent."
)
@func_parameter(
    "caller_intent",
    "The caller's intent. Must be one of: GENERAL_QUESTION, COMPLAINT, MAKE_APPOINTMENT, CONFIRM_APPOINTMENT, MODIFY_APPOINTMENT, CANCEL_APPOINTMENT, BILLING_QUESTION, CANCEL_SUBSCRIPTION, INSPECTION_REQUEST, NEW_SALE, COMMERCIAL_SERVICE, CALL_BACK, WELCOME_CALL, SPANISH",
)
def route_call(conv: Conversation, caller_intent: str):
    intent = caller_intent.strip().upper() if caller_intent else "GENERAL_QUESTION"
    if not intent:
        intent = "GENERAL_QUESTION"
    destination = INTENT_TO_ROUTE.get(intent, "CUSTOMER_CARE")

    conv.write_metric("PRIMARY_INTENT", intent)

    return conv.functions.handoff(
        intent,
        "One moment please while I transfer your call.",
        destination,
    )
