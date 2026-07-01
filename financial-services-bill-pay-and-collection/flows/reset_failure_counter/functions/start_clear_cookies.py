from _gen import *  # <AUTO GENERATED>


@func_description("User wants to clear their cookies — start the walkthrough")
def start_clear_cookies(conv: Conversation, flow: Flow):
    flow.goto_step("Clear Cookies Walkthrough")
    return {
        "utterance": "Great, you might want to put me on speaker whilst we go through this. Can I just check first, are you using a mobile or a computer?"
    }
