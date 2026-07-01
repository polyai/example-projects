from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


@func_description("Return a hard-coded OOD response")
def ood_response(conv: Conversation):
    if not conv.state.ood_counter:
        conv.state.ood_counter = 0

    conv.state.ood_counter += 1

    if conv.state.ood_counter > 1:
        conv.state.ood_response = True
        return handoff(
            conv,
            "OOD_LOOP",
            "Let me transfer you to someone who can help with this. Please hold the line.",
            "CUSTOMER_CARE",
        )
    if conv.state.ood_counter > 0:
        return {"utterance": "Would you mind saying that again?"}
