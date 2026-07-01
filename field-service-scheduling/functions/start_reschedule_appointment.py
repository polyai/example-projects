from _gen import *  # <AUTO GENERATED>
from functions.start_verify_user import start_verify_user


@func_description("Enter the reschedule_appointment flow")
@func_parameter(
    "another_appointment",
    "set to True if the user has indicated that they want to reschedule another appointment, not the same one they just confirmed or made, if they have just done that. Set to False if no appointment was just confirmed or made",
)
def start_reschedule_appointment(conv: Conversation, another_appointment: bool):
    # In-hours guard: route to queue instead of handling appointment
    if conv.state.routing_enabled:
        return conv.functions.route_call("MODIFY_APPOINTMENT")
    conv.state.call_intent = "reschedule"
    conv.write_metric("PRIMARY_INTENT", "MODIFY_APPOINTMENT")
    if not conv.state.user_verified:
        return start_verify_user(conv)
    else:
        if conv.state.appointment and not another_appointment:
            conv.write_metric("MODIFY_APPOINTMENT_FLOW_INITIATED", None)
            conv.goto_flow("reschedule_appointment")
        else:
            conv.write_metric("CONFIRM_APPOINTMENT_FLOW_INITIATED", None)
            conv.goto_flow("confirm_appointment")
