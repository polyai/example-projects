from _gen import *  # <AUTO GENERATED>


def end_function(conv: Conversation):
    outcome = "HANDOFF" if conv.state.handoff_reason else "CONTAINED"
    conv.write_metric("CALL_OUTCOME", outcome)
    if conv.state.task:
        conv.write_metric("TASK_UNFINISHED", conv.state.task)
