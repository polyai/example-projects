from _gen import *  # <AUTO GENERATED>


@func_description(
    "user has mentioned they are using a personal account for a domestic payee"
)
def user_has_personal_account(conv: Conversation, flow: Flow):
    flow.goto_step("collect payee bank information")
    return {
        "utterance": "And is this going to a Poly Bank account or a different bank?"
    }
