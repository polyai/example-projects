from _gen import *  # <AUTO GENERATED>


@func_description("collect and save if the user wants to reschedule rather than canceling")
@func_parameter(
    "reschedule_not_cancel",
    "set to True if the user agrees to reschedule the appointment, instead of cancelling it. set to False if the user wants to proceed with cancelling the appointment",
)
def reschedule_not_cancel(conv: Conversation, flow: Flow, reschedule_not_cancel: bool):
    if reschedule_not_cancel:
        conv.write_metric("MODIFY_APPOINTMENT_FLOW_INITIATED", None)
        conv.goto_flow("reschedule_appointment")
        return "You now need to reschedule the appointment for the user."
    else:
        flow.goto_step("Collect cancel reason")
