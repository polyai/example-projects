from _gen import *  # <AUTO GENERATED>

from .mock_api import MockAccountLookup


@func_description(
    "Process a payment over the phone. Only call this after the customer has been verified and chose to pay over the phone."
)
@func_parameter("account_number", "the verified account number")
@func_parameter("amount", "the payment amount in dollars")
def process_payment(conv: Conversation, account_number: str, amount: float):
    result = MockAccountLookup.make_payment(account_number, amount)
    if result is None:
        return {
            "content": "Account not found. Ask the user to verify their account number."
        }
    if "error" in result:
        return {
            "content": f"Payment failed: {result['error']}. Let the user know and offer alternatives."
        }

    conv.state.last_confirmation_number = result["confirmation_number"]
    return {
        "content": (
            f"Payment of ${amount:.2f} processed successfully. "
            f"Confirmation number: {result['confirmation_number']}. "
            f"New balance: ${result['new_balance']:.2f}. "
            f"Read the confirmation number to the user and ask if there's anything else you can help with."
        ),
    }
