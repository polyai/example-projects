from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff
from functions.routes_api_call import (
    get_office,
    get_service_type_id_for_warranty_reservice,
    get_subscriptions,
    search_services,
)


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

    known_office_ids = [
        "732",
        "734",
        "750",
        "746",
        "219",
        "741",
        "726",
        "719",
        "751",
        "603",
        "736",
        "11",
        "10",
        "745",
        "748",
        "737",
        "15",
        "604",
        "749",
        "753",
        "725",
        "757",
        "747",
        "754",
        "712",
        "756",
        "733",
        "718",
        "606",
        "755",
        "602",
        "738",
    ]
    customer_details_list = [
        customer for customer in customer_details_list if customer["officeID"] in known_office_ids
    ]
    if not customer_details_list:  # should not happen in practice
        return handoff(
            conv,
            "CUSTOMER_AT_UNKNOWN_LOCATION",
            "Let me put you through to someone who can help, just a moment please!",
            "CUSTOMER_CARE",
        )

    zipcodes = [customer["zip"] for customer in customer_details_list]
    zipcodes_matched = []
    for customer_zipcode in zipcodes:
        if zipcode[:5] == customer_zipcode[:5]:
            if zipcode in zipcodes_matched:
                return handoff(
                    conv,
                    "CUSTOMER_WITH_MULTIPLE_PROPERTIES_AT_ZIPCODE",
                    "I see that you have multiple properties at this zipcode. Let me put you through to someone who can help, just a moment please!",
                    "CUSTOMER_CARE",
                )
            else:
                zipcodes_matched.append(zipcode)

    for customer_details in customer_details_list:
        customer_details_zipcode = customer_details["zip"]

        if zipcode[:5] == customer_details_zipcode[:5]:
            conv.log.info("Given zipcode matches", zipcode=zipcode)
            conv.state.user_verified = True
            conv.write_metric("CUSTOMER_VERIFICATION_SUCCESSFUL", None)
            conv.state.customer_details = customer_details

            try:
                office = get_office(conv)
                conv.write_metric("CUSTOMER_OFFICE_LOCATION", office["officeName"])
            except Exception:
                conv.log.error("Error when getting office", exc_info=True)

            # Service type IDs and names are different for each location and the list can be updated, so we need to fetch them every time
            try:
                services = search_services(conv)
                conv.state.services_names = [
                    service["name"] for service in services
                ]  # used for ASR keyword biasing
                conv.state.services_map = [
                    {"serviceID": service["serviceID"], "name": service["name"]}
                    for service in services
                ]

                # also fetch service_type_id_for_warranty_reservice
                conv.state.service_type_id_for_warranty_reservice = (
                    get_service_type_id_for_warranty_reservice(conv)
                )
                if not conv.state.service_type_id_for_warranty_reservice:
                    conv.log.warning("location does not have Warranty Reservice service type")
                    handoff_reason = "NO_WARRANTY_RESERVICE_TYPE"
                    return handoff(
                        conv,
                        handoff_reason,
                        "Let me put you through to someone who can help, just a moment please!",
                        "CUSTOMER_CARE",
                    )
            except Exception:
                conv.log.error("Error when fetching services", exc_info=True)
                handoff_reason = "API_TIMEOUT" if conv.state.api_timeout else "API_ERROR"
                return handoff(
                    conv,
                    handoff_reason,
                    "I'm afraid I am facing some technical difficulties at this moment, let me put you through to someone who can help, just a moment please!",
                    "CUSTOMER_CARE",
                )

            # ie "Balance on account is +$20 and >30 days past due"
            if (
                float(customer_details["balance"]) > 20
                and float(customer_details["balanceAge"]) > 30
            ):
                return handoff(
                    conv,
                    "CUSTOMER_WITH_BALANCE_PAST_DUE",
                    "I see that you have a balance that's past due with us. Let me put you through to someone who can help, just a moment please!",
                    "CUSTOMER_CARE",
                )

            # ie "Pending Cancel Flag Checked on Account"
            if customer_details["pendingCancel"] != "0":
                return handoff(
                    conv,
                    "CUSTOMER_WITH_PENDING_CANCEL",
                    "I see that you have a pending cancellation. Let me put you through to someone who can help, just a moment please!",
                    "CUSTOMER_CARE",
                )

            subscriptions = []
            try:
                subscriptions = get_subscriptions(conv)
                subscriptions = [
                    subscription for subscription in subscriptions if subscription["active"] == "1"
                ]
                conv.state.subscriptions = subscriptions
                if len(subscriptions) == 0:
                    return handoff(
                        conv,
                        "FROZEN_CUSTOMER_ACCOUNT",
                        "I'm afraid I am seeing that your account has been frozen here, let me put you through to someone who can help, just a moment please!",
                        "CUSTOMER_CARE",
                    )
            except Exception:
                conv.log.error("Error when fetching subscriptions", exc_info=True)
                handoff_reason = "API_TIMEOUT" if conv.state.api_timeout else "API_ERROR"
                return handoff(
                    conv,
                    handoff_reason,
                    "I'm afraid I am facing some technical difficulties looking up your service at this moment, let me put you through to someone who can help, just a moment please!",
                    "CUSTOMER_CARE",
                )

            # ie "Exclude Commercial Quarterly, Monthly, Bi-Monthly"
            for subscription in subscriptions:
                if "commercial" in subscription["serviceType"].lower():
                    return handoff(
                        conv,
                        "COMMERCIAL_CUSTOMER",
                        "I'm going to transfer you to a colleague who specializes in business accounts and can take great care of you. One moment please.",
                        "CUSTOMER_CARE",
                    )

            # handoff if subscription not one of:
            # - Starts with “Quarterly”
            # - Monthly Maintenance
            # - Bi-Monthly Maintenance
            # - Bi-Monthly Maintenance Online
            # - BiMonthly Maintenance
            # - Organic Monthly
            # - Organic Bimonthly

            STANDARD_TYPES = [
                "monthly maintenance",
                "quarterly maintenance",
                "organic",
                "quarterly bundle maintenance",
            ]

            standard_subscription = next(
                (
                    subscription
                    for subscription in subscriptions
                    if any(
                        standard_type in subscription["serviceType"].lower()
                        for standard_type in STANDARD_TYPES
                    )
                ),
                None,
            )
            conv.state.subscription = standard_subscription

            has_specialized_subscription = any(
                "specialized" in subscription["serviceType"].lower()
                or "inspection" in subscription["serviceType"].lower()
                for subscription in subscriptions
            )

            if (
                not standard_subscription
                and has_specialized_subscription
                and len(subscriptions) == 1
            ):
                return handoff(
                    conv,
                    "SPECIALIZED_SERVICE",
                    "That's something we'll want to escalate to our specialists. One moment please while I connect you.",
                    "NS_SCHEDULING_INBOUND",
                )

            if not standard_subscription:
                return handoff(
                    conv,
                    "CUSTOMER_WITH_SUBSCRIPTION_OF_OTHER_TYPE",
                    "Thank you. Let me put you through to a colleague who can help you with this, just a moment please!",
                    "CUSTOMER_CARE",
                )

            if (
                conv.state.call_intent == "get_account_number"
            ):  # https://poly-ai.atlassian.net/browse/UTIL-2512
                flow.goto_step("Ask if ready for account number")
                return

            # TODO get is_already_clear_caller_asking_for_regular_service to work more reliably by tweaking function description before using here as an "or" condition
            if len(subscriptions) == 1:
                service_type = standard_subscription["serviceType"]
                prompt_to_return = f"""You have found the user's account and now know that they have a {service_type} subscription."""
                if conv.state.call_intent in ["reschedule", "confirm", "schedule", "cancel"]:
                    # reschedule and cancel have to go through confirm first
                    # schedule as well, to check that the caller doesn't already have an upcoming appointment https://poly-ai.atlassian.net/browse/UTIL-2544
                    conv.write_metric("CONFIRM_APPOINTMENT_FLOW_INITIATED", None)
                    conv.goto_flow("confirm_appointment")
                else:
                    conv.exit_flow()
                    conv.log.error(
                        "call_intent not set or does not have an expected value",
                        call_intent=conv.state.call_intent,
                    )
                return prompt_to_return
            else:
                flow.goto_step("Ask subscription type")
                if has_specialized_subscription:
                    return """Ask the user: "Just to check, will this be concerning an appointment for your regular service subscription, a specialized service, or one of your other subscriptions?"
        """
                return """Ask the user: "Just to check, will this be concerning an appointment for your regular service subscription, or will this be for one of your other subscriptions?"
        """

    if not conv.state.collect_zip_retried:
        conv.state.collect_zip_retried = True
        return {
            "content": f"The user gave a zipcode, {zipcode}, that doesn't match their account. Try to get it one more time.",
            "utterance": "Could you please try that zipcode one more time?",
        }

    return handoff(
        conv,
        "ZIPCODE_CHECK_FAIL",
        "Ok, let me put you through to a team member, one moment please!",
        "CUSTOMER_CARE",
    )
