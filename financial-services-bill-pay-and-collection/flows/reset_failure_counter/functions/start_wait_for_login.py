from _gen import *  # <AUTO GENERATED>


@func_description("User wants to stay on the line while they try logging in")
def start_wait_for_login(conv: Conversation, flow: Flow):
    flow.goto_step("Wait For Login")
    return {
        "utterance": "Sure, take your time and let me know how it goes.",
        "listen": {"asr": {"timeout": 20}},
    }
