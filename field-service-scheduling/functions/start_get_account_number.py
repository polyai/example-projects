from _gen import *  # <AUTO GENERATED>
from functions.start_verify_user import start_verify_user


@func_description("start get account number")
def start_get_account_number(conv: Conversation):
    # In-hours guard: route to queue instead of handling request
    if conv.state.routing_enabled:
        return conv.functions.route_call("GENERAL_QUESTION")
    conv.state.call_intent = "get_account_number"
    conv.write_metric("PRIMARY_INTENT", "GET_ACCOUNT_NUMBER")
    if not conv.state.user_verified:
        return start_verify_user(conv)
    else:
        return {
            "transition": {
                "goto_flow": "verify_user",
                "goto_step": "Ask if ready for account number",
            }
        }
