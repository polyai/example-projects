from _gen import *  # <AUTO GENERATED>
from functions import idnv


def account_number_instruction(conv) -> str:
    customer = idnv.customer(conv) or {}
    number = str(customer.get("account_number") or "")
    if not number:
        return "There's no account number on file to give. Say so and ask if there's anything else."
    conv.write_metric("ACCOUNT_NUMBER_GIVEN")
    words = " ".join(
        ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"][int(d)]
        for d in number
        if d.isdigit()
    )
    return (
        f'Tell the caller their account number is "{words}", one digit at a time, and offer to '
        "repeat it while they write it down."
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
