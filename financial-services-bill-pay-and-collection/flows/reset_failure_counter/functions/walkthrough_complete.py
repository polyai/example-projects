from _gen import *  # <AUTO GENERATED>


@func_description("The walkthrough or SMS offer is complete — exit the flow")
def walkthrough_complete(conv: Conversation, flow: Flow):
    conv.exit_flow()
    return "Continue helping the user with anything else they need."
