from _gen import *  # <AUTO GENERATED>


@func_description("the customer is ok to wait")
def customer_ok_to_wait_to_make_next_appointment(conv: Conversation, flow: Flow):
    conv.exit_flow()
    return "Ask the user if there is anything else you can help with"
