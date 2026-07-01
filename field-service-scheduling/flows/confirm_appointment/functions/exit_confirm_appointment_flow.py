from _gen import *  # <AUTO GENERATED>


@func_description("Exit the confirm_appointment flow")
def exit_confirm_appointment_flow(conv: Conversation, flow: Flow):
    conv.write_metric("CONFIRM_APPOINTMENT_FLOW_SUCCESSFUL", None)
    conv.exit_flow()
    return 'Say "Great! Is there anything else I can do for you today?"'
