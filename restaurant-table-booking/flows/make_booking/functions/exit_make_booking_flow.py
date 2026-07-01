from _gen import *  # <AUTO GENERATED>


@func_description("Stop making the booking")
def exit_make_booking_flow(conv: Conversation, flow: Flow):
    conv.exit_flow()
    return "Ask the user if there is anything else you can do for them."
