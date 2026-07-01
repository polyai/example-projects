from _gen import *  # <AUTO GENERATED>
from functions.start_verify_user import start_verify_user


@func_description("Enter the make_appointment flow")
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=4,
    delay_responses=[("One second please", 3)],
)
def start_make_appointment(conv: Conversation):
    # In-hours guard: route to queue instead of handling appointment
    if conv.state.routing_enabled:
        return conv.functions.route_call("MAKE_APPOINTMENT")
    conv.state.call_intent = "schedule"
    conv.write_metric("PRIMARY_INTENT", "MAKE_APPOINTMENT")
    if not conv.state.user_verified:
        return start_verify_user(conv)
    else:
        # first check that the caller doesn't already have an upcoming appointment https://poly-ai.atlassian.net/browse/UTIL-2544
        conv.write_metric("CONFIRM_APPOINTMENT_FLOW_INITIATED", None)
        conv.goto_flow("confirm_appointment")
