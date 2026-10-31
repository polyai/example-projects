from _gen import *  # <AUTO GENERATED>


@func_description(
    "System function for response control: the agent said it would transfer"
)
def handoff_no_arg(conv: Conversation):
    return {
        "content": "You told the caller you're putting them through but didn't. Call handoff now "
        "with the most fitting handoff_reason from your instructions and handoff_utterance="
        "'Let me put you through to the team. One moment please.'"
    }
