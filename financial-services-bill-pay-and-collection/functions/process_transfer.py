from _gen import *  # <AUTO GENERATED>

from .mock_api import MockAccountLookup


@func_description(
    "Process a transfer from the user's account. Call this after verifying the customer and collecting all recipient details."
)
@func_parameter("account_number", "the verified sender's account number")
@func_parameter("amount", "the transfer amount in dollars")
@func_parameter("recipient_name", "the recipient's full name")
@func_parameter("recipient_account", "the recipient's account number")
@func_parameter("transfer_type", '"DOMESTIC" or "INTERNATIONAL"')
@func_parameter(
    "swift_code",
    "the recipient bank's SWIFT/BIC code (international only, empty string for domestic)",
)
def process_transfer(
    conv: Conversation,
    account_number: str,
    amount: float,
    recipient_name: str,
    recipient_account: str,
    transfer_type: str,
    swift_code: str,
):
    conv.state.transfer_recipient_name = recipient_name
    conv.state.transfer_recipient_account = recipient_account
    conv.state.transfer_type = transfer_type
    if swift_code:
        conv.state.transfer_swift_code = swift_code

    result = MockAccountLookup.make_payment(account_number, amount)
    if result is None:
        return {"content": "Account not found. Ask the user to verify their account number."}
    if "error" in result:
        return {
            "content": f"Transfer failed: {result['error']}. Let the user know and offer alternatives."
        }

    conv.state.last_confirmation_number = result["confirmation_number"]
    return {
        "content": (
            f"Transfer of ${amount:.2f} to {recipient_name} processed successfully. "
            f"Confirmation number: {result['confirmation_number']}. "
            f"New balance: ${result['new_balance']:.2f}. "
            f"Read the confirmation number to the user and ask if there's anything else you can help with."
        ),
    }
