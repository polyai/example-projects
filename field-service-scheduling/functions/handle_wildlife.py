from _gen import *  # <AUTO GENERATED>


@func_description(
    "Call this when the user asks about wildlife removal (raccoons, snakes, bats, squirrels, birds, moles, voles, etc.)"
)
def handle_wildlife(conv: Conversation):
    if conv.state.routing_enabled:
        return conv.functions.route_call("GENERAL_QUESTION")

    return {
        "content": "Tell the user: We do not remove wildlife but would recommend looking for an animal control company in their area. "
        "Never schedule an appointment for wildlife. After answering, ask if you can help with anything else. Do not transfer."
    }
