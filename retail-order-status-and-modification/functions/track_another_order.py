from _gen import *  # <AUTO GENERATED>

from .utterances import utterance


@func_description(
    "Tracks another ORDER for the user. They will have to complete IDNV again with new order details. DO NOT call this if they just want to track another ITEM in their order."
)
def track_another_order(conv: Conversation):
    if conv.state.using_calling_number and len(conv.state.orders_from_phone_number) > 1:
        return {
            "utterance": utterance(conv, "track_another_caller_number"),
            "transition": {
                "goto_flow": "OMS_IDNV",
                "goto_step": "Check should collect phone number",
            },
        }
    elif (
        conv.state.use_alternative_number
        and len(conv.state.orders_from_phone_number) > 1
    ):
        return {
            "utterance": utterance(conv, "track_another_same_number"),
            "transition": {
                "goto_flow": "OMS_IDNV",
                "goto_step": "Check should collect phone number",
            },
        }
    elif conv.state.order_from_full_order_number:
        return {
            "utterance": utterance(conv, "track_another_order_number"),
            "transition": {
                "goto_flow": "OMS_IDNV",
                "goto_step": "Collect full order number",
            },
        }
    else:
        return {
            "utterance": utterance(conv, "track_another_phone_number"),
            "transition": {
                "goto_flow": "OMS_IDNV",
                "goto_step": "Collect phone number",
            },
        }
