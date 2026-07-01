from _gen import *  # <AUTO GENERATED>


@func_description(
    "function to call if the user doesn't want to use the number they are calling from"
)
def user_wants_other_number(conv: Conversation, flow: Flow):
    flow.goto_step("Phone number collected")
