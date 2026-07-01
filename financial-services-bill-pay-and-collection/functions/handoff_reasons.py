from _gen import *  # <AUTO GENERATED>
from functions.handoff import ALL_VALID_HANDOFF_REASONS


def get_valid_handoff_reasons() -> str:
    return ", ".join(ALL_VALID_HANDOFF_REASONS)


@func_description("utils function for valid handoff reasons")
def handoff_reasons(conv: Conversation):
    conv.state.handoff_reasons = get_valid_handoff_reasons()
