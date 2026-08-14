from _gen import *  # <AUTO GENERATED>
from functions.step_utils import is_ca_from_state


@func_description("Guides the user in how to start a return.")
@func_parameter("buying_method", "Either Instore or Online")
def start_returns_walkthrough(conv: Conversation, buying_method: str):
    conv.write_metric("RETURNS_WALKTHROUGH")

    is_ca = is_ca_from_state(conv)

    if buying_method == "Instore" and is_ca:
        # CA in-store: Distribution Centre cannot accept store returns
        conv.state.prompt = (
            "Tell the user that since they purchased the item in store, "
            "they'll need to return it to the "
            "store. Unfortunately, we're unable to provide a return label "
            "for items purchased in store, as our Distribution Centre "
            "cannot accept store returns. "
            'Then ask "Is there anything else I can help you with?"'
        )
        return conv.state.prompt

    instructions_header = """Give the user the instructions below. Give one step at a time and stick to the wording as much as possible. Once you say a step, wait for the user's response - you do not need to check if they have done it after each step). Each step starts with "#": \n """
    instructions_footer = """If the user is silent for a turn after you have given them a step, DO NOT say anything. DO NOT ask if they have completed the step. Instead, wait for up to TWO turns or until the user responds (they might say something like "ok" when they are ready).\n
        If the user asks you to wait while you are giving them the steps, wait for them to catch up before you continue.\n
        If the user is silent for THREE consecutive turns after you give them the steps, DO NOT say goodbye or end the call, DO NOT SAY ANYTHING - just wait for them to respond. After the FOURTH time the user is silent, check if they have managed to do it.\n
        If you have told the user how to do this online, ask "Is there anything else I can help you with?"""
    if buying_method == "Instore":
        instructions_body = f"""
    # Okay, first go to {(conv.variant or {}).get("returns_url", "")}. and let me know when you're there.\n
    # Now,  click on Purchased at Retail location and fill in all the information you can. You don't have to enter anything marked as optional.\n
    --- If the user asks for  help in answering specific questions:\n
    ------- The weight of the package is optional, but for reference, a pair of adult sneakers is likely to weigh between 2 and 4 pounds. \n
    ------- The SKU code is optional but can be found on your receipt, next to the description of the item. \n
    # Once you've entered the item or items you want to return, click continue, and select Refund or Exchange for each item. If you want to make an exchange, you'll need to give the product number and size of the item you want instead.\n
    # After entering your exchange details, enter the full address you'll be shipping from. \n
    # Then, save your address and confirm your return or exchange!"""
        conv.state.prompt = (
            instructions_header + instructions_body + instructions_footer
        )
        return conv.state.prompt
