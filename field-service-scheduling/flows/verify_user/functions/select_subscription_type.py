from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


@func_description(
    "Select the subscription type based on what the user has said, on whether it is for their regular service subscription or not"
)
@func_parameter(
    "is_for_regular_service",
    "True if the caller is calling about an appointment for their regular service subscription, False in all other cases",
)
@func_parameter(
    "is_specialized_service",
    "True if the caller is calling about a specialized service appointment (e.g. assessment, specialty work), False in all other cases",
)
def select_subscription_type(
    conv: Conversation,
    flow: Flow,
    is_for_regular_service: bool,
    is_specialized_service: bool,
):
    # handoff if subscription not one of:
    # - Starts with "Quarterly"
    # - Monthly Maintenance
    # - Bi-Monthly Maintenance
    # - Bi-Monthly Maintenance Online
    # - BiMonthly Maintenance
    # - Organic Monthly
    # - Organic Bimonthly

    if is_specialized_service:
        return handoff(
            conv,
            "SPECIALIZED_SERVICE",
            "That's something we'll want to escalate to our specialists. One moment please while I connect you.",
            "NS_SCHEDULING_INBOUND",
        )

    if not is_for_regular_service:
        return handoff(
            conv,
            "CUSTOMER_WITH_SUBSCRIPTION_OF_OTHER_TYPE",
            "Thank you. Let me put you through to a colleague who can help, just a moment please!",
            "CUSTOMER_CARE",
        )

    subscription = conv.state.subscription
    if subscription is None:
        raise ValueError("subscription must be set before calling this function")
    service_type = subscription["serviceType"]
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
