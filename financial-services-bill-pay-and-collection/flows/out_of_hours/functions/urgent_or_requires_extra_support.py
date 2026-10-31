from _gen import *  # <AUTO GENERATED>


@func_description("The caller says their call is urgent or they need extra support.")
def urgent_or_requires_extra_support(conv: Conversation, flow: Flow):
    conv.write_metric("OOH_URGENT_CALL")
    conv.exit_flow()
    return "The caller's issue is urgent or needs extra support. Ask what you can help with, and help them as normal."
