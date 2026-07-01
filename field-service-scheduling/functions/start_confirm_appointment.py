from _gen import *  # <AUTO GENERATED>
from functions.start_verify_user import start_verify_user


@func_description("Enter the confirm_appointment flow")
@func_latency_control(
    delay_before_responses_start=3,
    silence_after_each_response=10,
    delay_responses=[("just a moment please", 3)],
)
def start_confirm_appointment(conv: Conversation):
    # In-hours guard: route to queue instead of handling appointment
    if conv.state.routing_enabled:
        return conv.functions.route_call("CONFIRM_APPOINTMENT")
    conv.state.call_intent = "confirm"
    conv.write_metric("PRIMARY_INTENT", "CONFIRM_APPOINTMENT")
    if not conv.state.user_verified:
        return start_verify_user(conv)
    else:
        conv.write_metric("CONFIRM_APPOINTMENT_FLOW_INITIATED", None)
        conv.goto_flow("confirm_appointment")
