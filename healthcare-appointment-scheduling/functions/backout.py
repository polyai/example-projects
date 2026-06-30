from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Agent Behaviour] Call to exit the current flow or process. Once you call this function, you will be able to do something else, but you won't be able to continue with the current process unless you call the relevant functions again."
)
def backout(conv: Conversation):
    # Write metric
    conv.write_metric("BACKOUT")

    # Exit current flow
    conv.exit_flow()
    return
