from _gen import *  # <AUTO GENERATED>


@func_description("user has mentioned they want to make a payment from a business account")
def user_has_business_account(conv: Conversation, flow: Flow):
    flow.goto_step("user has business account")
