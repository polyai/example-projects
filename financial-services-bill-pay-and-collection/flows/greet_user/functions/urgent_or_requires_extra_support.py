from _gen import *  # <AUTO GENERATED>


@func_description("The user says their issue is urgent or requires extra support")
def urgent_or_requires_extra_support(conv: Conversation, flow: Flow):
    conv.write_metric("OOH_URGENT_CALL")
    conv.exit_flow()
    return "The user's issue is urgent or requires extra support. Help them as normal, including calling the 'handoff' function where instructed to do so."
