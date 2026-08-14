from _gen import *  # <AUTO GENERATED>
from datetime import datetime


from .mock_api import MockAccountLookup


def _mask_account_number(account_number: str) -> str:
    """Redact all but the last 4 digits for safe logging (e.g. '******7890').

    Identifiers of 4 characters or fewer are masked in full, so a short account
    number never lands in logs unredacted.
    """
    if not account_number:
        return ""
    if len(account_number) <= 4:
        return "*" * len(account_number)
    return "*" * (len(account_number) - 4) + account_number[-4:]


def _format_date(iso_date: str) -> str:
    """Convert '2026-07-01' to 'July 1st'."""
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    day = dt.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{dt.strftime('%B')} {day}{suffix}"


@func_description(
    "Look up account balance by account number. Call this when the user wants to check their balance and has provided their account number."
)
@func_parameter("account_number", "the user's account number (digits only)")
def check_balance(conv: Conversation, account_number: str):
    account = MockAccountLookup.get_account(account_number)
    if not account:
        attempts = (conv.state.account_lookup_attempts or 0) + 1
        conv.state.account_lookup_attempts = attempts
        conv.log.info(
            "check_balance: account not found",
            account_number=_mask_account_number(account_number),
            attempts=attempts,
        )
        if attempts < 3:
            return {
                "content": (
                    f"That account number was NOT found (attempt {attempts} of 3). "
                    "Apologize briefly and ask the user to read out their account number again, "
                    "e.g. \"Sorry, I can't find that account in our system — could you read me "
                    'your account number again?" Do NOT read the account number back to the '
                    "caller, and do NOT offer a transfer yet; just re-collect the account number "
                    "so we can try once more."
                ),
            }
        return {
            "content": (
                f"That account number was NOT found after {attempts} attempts. "
                "Tell the user you're unable to locate their account and offer to transfer them "
                "to an agent. Do NOT read the account number back to the caller."
            ),
        }

    conv.log.info(
        "check_balance: account found",
        account_number=_mask_account_number(account_number),
    )
    conv.state.account_lookup_attempts = 0
    conv.state.verified_account = account_number
    conv.state.account_holder_name = account["name"]
    conv.state.account_dob = account["dob"]
    conv.state.account_balance = account["balance"]

    pending = account.get("pending_payments", [])
    pending_info = ""
    if pending:
        items = [
            f"${p['amount']:.2f} to {p['recipient']} on {_format_date(p['scheduled_date'])}"
            for p in pending
        ]
        pending_info = (
            f" You also have {len(pending)} pending payment(s): {', '.join(items)}."
        )

    return {
        "content": (
            f"Account FOUND for {account['name']}. "
            f"Before reading out the balance, you MUST verify the user's identity. "
            f"Ask: 'For security, can you confirm the date of birth on the account?' "
            f"The correct DOB is {account['dob']}. "
            f"If the user's answer matches, say: 'Your current balance is ${account['balance']:.2f}.{pending_info}' "
            f"If it does NOT match, say you can't share account details for security reasons and offer to transfer to an agent."
        ),
    }
