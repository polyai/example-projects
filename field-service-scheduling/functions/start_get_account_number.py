from _gen import *  # <AUTO GENERATED>
from functions import idnv

NO_NUMBER = "I'm sorry, I can't see an account number on file. Is there anything else I can help with?"


def account_number_instruction(conv) -> str:
    """The account number, spelled digit by digit in groups of four, always 'zero', never 'oh'."""
    customer = idnv.customer(conv) or {}
    number = str(customer.get("account_number") or "")
    if not number:
        return f'Say: "{NO_NUMBER}"'
    conv.write_metric("ACCOUNT_NUMBER_GIVEN")
    return (
        f'Say exactly: "Your account number is {idnv.spell_id(number)}." Then ask "Would you like '
        'me to say that again?" and repeat it the same way if they ask.'
    )


@func_description("The caller wants to know their account number.")
def start_get_account_number(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "GET_ACCOUNT_NUMBER")
    gate = idnv.require(conv, "account_number")
    if gate:
        return gate
    if conv.current_flow:  # leave the task the caller switched away from
        conv.exit_flow()
    return account_number_instruction(conv)
