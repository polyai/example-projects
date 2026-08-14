from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


@func_description(
    "Check the zip code to complete user verification if the zip code matches the retrieved details"
)
@func_parameter(
    "zipcode",
    'zip code given by the caller. ignore punctuation and spaces eg if you see "7501 4" just take it as "75014". Remember that Oh is 0, eg Oh 8736 is 08736. if you receive a 9-digit zipcode, keep the hyphen in eg as 12345-6789',
)
@func_parameter(
    "declined_or_unknown",
    'Default to False. Set to True only if the user explicitly declines to give their zipcode - "no", "I don\'t want to give you my zipcode" - or explicitly states that they do not know their zipcode - "I don\'t know it".',
)
@func_parameter(
    "is_already_clear_caller_asking_for_regular_service",
    "set to True if it is already clear to you that the caller wants an appointment for their regular service (excluding specialty services, in those cases definitely set to False), otherwise set to False if the caller has just said something about an appointment(s) without explicitly specifying what type",
)
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=3,
    delay_responses=[
        ("Let me check that real quick", 3),
        ("just another second please", 3),
        ("sorry it's taking a bit ...", 3),
        ("okay, let's see...", 3),
    ],
)
def should_save_zip_code(
    conv: Conversation,
    flow: Flow,
    zipcode: str,
    declined_or_unknown: bool,
    is_already_clear_caller_asking_for_regular_service: bool,
):
    customer_details_list = conv.state.customer_details_list
    conv.write_metric("ZIPCODE_COLLECTED", None)

    if declined_or_unknown:
        return handoff(
            conv,
            "ZIPCODE_NOT_PROVIDED",
            "I'm sorry, but I need your zipcode to continue. Let me put you through to someone who can help, just a moment please!",
            "CUSTOMER_CARE",
        )

    # Mock mode: simple zip match without real API calls
    if getattr(conv.state, "USE_MOCK_API", False):
        matched = next(
            (c for c in customer_details_list if zipcode[:5] == c.get("zip", "")[:5]),
            None,
        )
        if not matched:
            if not conv.state.collect_zip_retried:
                conv.state.collect_zip_retried = True
                return {
                    "content": f"The zipcode {zipcode} doesn't match. Ask the user to try again.",
                    "utterance": "Could you please try that zipcode one more time?",
                }
            return handoff(
                conv,
                "ZIPCODE_CHECK_FAIL",
                "Ok, let me put you through to a team member, one moment please!",
                "CUSTOMER_CARE",
            )

        conv.state.user_verified = True
        conv.state.customer_details = matched
        conv.state.customer_id = matched["customerID"]
        conv.write_metric("CUSTOMER_VERIFICATION_SUCCESSFUL", None)

        from functions.mock_api import SERVICE_TYPES

        conv.state.service_type_ids = [st["typeID"] for st in SERVICE_TYPES]
        conv.state.service_type_id_for_warranty_reservice = "ST-001"
        from datetime import datetime, timedelta

        next_month = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        conv.state.subscription = {
            "subscriptionID": "SUB-001",
            "serviceID": "ST-001",
            "serviceType": "General Service",
            "active": "1",
            "nextService": next_month,
        }
        conv.state.subscriptions = [conv.state.subscription]

        if conv.state.call_intent == "schedule":
            conv.goto_flow("schedule_appointment")
            return "You have verified the customer. They want to schedule a new appointment. Collect the service details."
        elif conv.state.call_intent in ["reschedule", "confirm", "cancel"]:
            conv.write_metric("CONFIRM_APPOINTMENT_FLOW_INITIATED", None)
            conv.goto_flow("confirm_appointment")
            return "You have verified the customer. Retrieving their existing appointments."
        else:
            conv.exit_flow()
            return "You have verified the customer's identity. They have a General Service subscription."

    # ── Real API path ──────────────────────────────────────────────────
    # TODO: Implement your own customer verification logic here.
    # Typical steps:
    #   1. Match zipcode against customer_details_list
    #   2. Fetch office info, services, and subscriptions from your dispatch API
    #   3. Check for account holds, balances, or special subscription types
    #   4. Route to the appropriate flow based on call_intent
    raise NotImplementedError(
        "Real API verification path not implemented — connect your dispatch API"
    )
