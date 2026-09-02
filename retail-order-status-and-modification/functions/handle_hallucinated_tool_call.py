from _gen import *  # <AUTO GENERATED>


@func_description(
    "DO NOT CALL, this is just a reminder to call tools when they should be called, instead of outputting text"
)
def handle_hallucinated_tool_call(conv: Conversation):
    # Add your function definition here.
    # You can optionally return a string that will be fed back to the LLM.
    return "You were tried to say something that indicated you are trying to call a tool. Call the correct tool instead immediately without saying anything."
