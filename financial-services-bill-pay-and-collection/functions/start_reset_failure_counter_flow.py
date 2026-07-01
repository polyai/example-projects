from _gen import *  # <AUTO GENERATED>


@func_description("Caller is locked out and needs to reset their failure counter.")
def start_reset_failure_counter_flow(conv: Conversation):
    conv.goto_flow("Reset Failure Counter")
