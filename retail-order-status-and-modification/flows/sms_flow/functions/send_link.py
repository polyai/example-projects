from _gen import *  # <AUTO GENERATED>
from functions import idnv, orders, sms

TOOL = "send_link"


@func_description(
    "Settle the number to text the link to, read it back and send it. Call it whenever the caller answers about the number, even if they repeat the same one."
)
@func_parameter(
    "use_calling_number",
    "'true' only if the caller's latest reply agreed to the question about texting the number they're calling from ('okay', 'sure' or 'go on' to that question is agreement), or they asked for that themselves. Otherwise 'false'.",
)
@func_parameter(
    "phone_number",
    "The number to text, as the caller said it (words or digits): the one they just gave, or, with number_confirmed='true', the number they agreed to. Never add or guess digits. Empty string if none.",
)
@func_parameter(
    "number_confirmed",
    "'true' only if the caller's latest reply agreed to the readback question this tool returned for the number. 'Okay', 'sure', 'sounds good' or 'go on' in answer to that question is agreement; a corrected number, an answer to something else, or real hesitation is not. Otherwise 'false'.",
)
def send_link(
    conv: Conversation,
    flow: Flow,
    use_calling_number: str,
    phone_number: str,
    number_confirmed: str,
):
    calling = sms.calling_number(conv)
    current = (
        (conv.state.sms or {}).get("id", "") if isinstance(conv.state.sms, dict) else ""
    )

    if str(phone_number or "").strip():
        said = sms.pending_number(conv)
        digits = idnv.normalize_phone(phone_number)
        if str(number_confirmed).strip().lower() == "true" and said and digits == said:
            if orders.same_turn_as_ask(conv, sms.SMS_KEY):
                return orders.wait_for_answer(conv, sms.SMS_KEY)
            result = sms.send(conv, said, to_calling=False)
            conv.exit_flow()
            return result
        return sms.take_number(conv, phone_number, TOOL)

    if str(number_confirmed).strip().lower() == "true" and sms.pending_number(conv):
        if orders.same_turn_as_ask(conv, sms.SMS_KEY):
            return orders.wait_for_answer(conv, sms.SMS_KEY)
        result = sms.send(conv, sms.pending_number(conv), to_calling=False)
        conv.exit_flow()
        return result

    if str(use_calling_number).strip().lower() == "true" and calling:
        if sms.offered(conv, current) and (conv.state.sms or {}).get("calling"):
            if orders.same_turn_as_ask(conv, sms.SMS_KEY):
                return orders.wait_for_answer(conv, sms.SMS_KEY)
            result = sms.send(conv, calling, to_calling=True)
            conv.exit_flow()
            return result
        question = sms.ask_calling_number(conv, current)
        return f"Ask: \"{question}\" {orders.YES_LINE}: call {TOOL} with use_calling_number='true'."

    if calling:
        question = sms.ask_calling_number(conv, current)
        return (
            f"Ask: \"{question}\" {orders.YES_LINE}: call {TOOL} with use_calling_number='true'. "
            f"If they give another number, call {TOOL} with it."
        )
    return f'Ask: "{sms.NUMBER_ASK}" {orders.call_again(TOOL)}'
