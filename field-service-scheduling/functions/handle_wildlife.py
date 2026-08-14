from _gen import *  # <AUTO GENERATED>


@func_description("Call this when the user asks about a service outside our scope")
def handle_wildlife(conv: Conversation):
    if conv.state.routing_enabled:
        return conv.functions.route_call("GENERAL_QUESTION")

    return {
        "content": "Tell the user: That's not a service we currently offer, but we'd recommend looking for a specialist in their area. "
        "Never schedule an appointment for out-of-scope services. After answering, ask if you can help with anything else. Do not transfer."
    }
