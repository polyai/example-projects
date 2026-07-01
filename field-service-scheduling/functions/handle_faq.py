from _gen import *  # <AUTO GENERATED>


@func_description(
    "Call this function when the user asks a general FAQ question (e.g. visit timing, service duration, visit prep, whether they need to be home, how many visits they get, etc.)"
)
@func_parameter("answer", "The answer to give the user if we are not in routing mode")
def handle_faq(conv: Conversation, answer: str):
    if conv.state.routing_enabled:
        return conv.functions.route_call("GENERAL_QUESTION")

    return {"content": answer}
