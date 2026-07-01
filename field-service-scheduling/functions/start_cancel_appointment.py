from _gen import *  # <AUTO GENERATED>
from functions.start_verify_user import start_verify_user


@func_description("Enter the cancel_appointment flow")
@func_parameter(
    "another_appointment",
    "set to True if the user has indicated that they want to cancel another appointment, not the same one they just confirmed, rescheduled, or made, if they have just done that. Set to False otherwise",
)
def start_cancel_appointment(conv: Conversation, another_appointment: bool):
    # In-hours guard: route to queue instead of handling appointment
    if conv.state.routing_enabled:
        return conv.functions.route_call("CANCEL_APPOINTMENT")
    if conv.real_time_config.get("settings", {}).get("cancel_appointment_flow_enabled"):
        conv.state.call_intent = "cancel"
        conv.write_metric("PRIMARY_INTENT", "CANCEL_APPOINTMENT")
        if not conv.state.user_verified:
            return start_verify_user(conv)
        else:
            if conv.state.appointment and not another_appointment:
                conv.write_metric("CANCEL_APPOINTMENT_FLOW_INITIATED", None)
                conv.goto_flow("cancel_appointment")
            else:
                conv.write_metric("CONFIRM_APPOINTMENT_FLOW_INITIATED", None)
                conv.goto_flow("confirm_appointment")
    else:
        return conv.functions.handoff(
            "CANCEL_APPOINTMENT",
            "For cancellations, I'll need to put you through to a colleague. One moment please.",
            "CUSTOMER_CARE",
        )
