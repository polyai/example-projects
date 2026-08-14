from _gen import *  # <AUTO GENERATED>


@func_description(
    "Save a confirmed recipient detail to state. Call this EVERY TIME the user confirms a detail (first name, last name, SWIFT code, or account number)."
)
@func_parameter(
    "field",
    'The field name: "first_name", "last_name", "swift_code", or "account_number"',
)
@func_parameter("value", "The confirmed value")
@func_parameter("transfer_type", '"DOMESTIC" or "INTERNATIONAL"')
@func_parameter(
    "amount",
    "The transfer amount in dollars. Required on the first call (first_name), optional after that. Default 0.",
)
def save_recipient_detail(
    conv: Conversation, field: str, value: str, transfer_type: str, amount: float
):
    field = field.lower().strip()
    conv.state[f"recipient_{field}"] = value

    if amount and amount > 0:
        conv.state.pending_payment_amount = amount

    is_international = transfer_type.upper() == "INTERNATIONAL"

    if field == "first_name":
        return {
            "content": (
                f"Saved recipient first name: {value}. "
                f'Now ask: "And their last name?" '
                f"When they answer, spell it back letter by letter to confirm. "
                f"Once confirmed, call {{{{fn:save_recipient_detail}}}} with field='last_name'."
            ),
        }

    if field == "last_name":
        if is_international:
            return {
                "content": (
                    f"Saved recipient last name: {value}. "
                    f"Now ask: \"What's the recipient bank's SWIFT code?\" "
                    f"When they answer, read it back character by character to confirm. "
                    f"Once confirmed, call {{{{fn:save_recipient_detail}}}} with field='swift_code'."
                ),
            }
        return {
            "content": (
                f"Saved recipient last name: {value}. "
                f"Now ask: \"What's the recipient's account number?\" "
                f"When they answer, read it back digit by digit to confirm. "
                f"Once confirmed, call {{{{fn:save_recipient_detail}}}} with field='account_number'."
            ),
        }

    if field == "swift_code":
        return {
            "content": (
                f"Saved SWIFT code: {value}. "
                f'Now ask: "And the recipient\'s account number?" '
                f"When they answer, read it back digit by digit to confirm. "
                f"Once confirmed, call {{{{fn:save_recipient_detail}}}} with field='account_number'."
            ),
        }

    if field == "account_number":
        first = getattr(conv.state, "recipient_first_name", "") or ""
        last = getattr(conv.state, "recipient_last_name", "") or ""
        swift = getattr(conv.state, "recipient_swift_code", "") or ""
        amount = getattr(conv.state, "pending_payment_amount", 0) or 0
        account = getattr(conv.state, "verified_account", "") or ""
        full_name = f"{first} {last}"

        if is_international:
            return {
                "content": (
                    f"Saved recipient account number: {value}. "
                    f"All details collected. Confirm with the user: "
                    f"\"Just to confirm, you'd like to send ${amount:.2f} to {full_name}, "
                    f'SWIFT code {swift}, account {value}. Is that correct?" '
                    f"Once confirmed, call {{{{fn:process_transfer}}}} with "
                    f"account_number='{account}', amount={amount}, "
                    f"recipient_name='{full_name}', recipient_account='{value}', "
                    f"transfer_type='INTERNATIONAL', swift_code='{swift}'."
                ),
            }
        return {
            "content": (
                f"Saved recipient account number: {value}. "
                f"All details collected. Confirm with the user: "
                f"\"Just to confirm, you'd like to send ${amount:.2f} to {full_name} "
                f'at account {value}. Is that correct?" '
                f"Once confirmed, call {{{{fn:process_transfer}}}} with "
                f"account_number='{account}', amount={amount}, "
                f"recipient_name='{full_name}', recipient_account='{value}', "
                f"transfer_type='DOMESTIC', swift_code=''."
            ),
        }

    return {
        "content": f"Unknown field '{field}'. Use first_name, last_name, swift_code, or account_number."
    }
