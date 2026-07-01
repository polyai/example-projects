from _gen import *  # <AUTO GENERATED>
from functions.utterances import utterance


@func_description("Determine what the user needs next.")
def ask_what_user_needs_next(conv: Conversation, flow: Flow):
    # if conv.state.remaining_items and len(conv.state.remaining_items) >= 1:
    if conv.state.looked_at and len(conv.state.looked_at) < conv.state.total_order_lines:
        if conv.state.user_wants_all_items:
            return {
                "utterance": utterance(conv, "wismo_next_item"),
                # "content": f""  """,
                "transition": flow.goto_step("Determine what user needs next"),
            }
        else:
            return {
                # "utterance": "No problem. Is there anything else I can help with, like tracking the status of the other items in the order?",
                "content": """If they haven't already just asked to track another item, ask if there's anything else you can help with, like tracking the status of the other items in the order.""",
                "transition": flow.goto_step("Determine what user needs next"),
            }
    else:
        return {
            # "utterance": "Okay. And is there anything else I can help with?",
            "content": """If the user hasn't already mentioned something else that they need help with, ask if there's anything else you can help with. \n
           IF THE USER HAS ASKED TO SPEAK TO AN AGENT, SAY: "I may be able to help you myself" and ask what the issue is.""",
            "transition": flow.goto_step("Determine what user needs next"),
        }


#   flow.goto_step("Determine what user needs next")
