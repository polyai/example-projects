"""Billing API client: accounts, amounts due, payment methods on file and payments.

Every tool reads and writes through this module, so connecting a real billing
system means replacing the bodies of the helpers below and nothing else.

Mock or real (see use_mock_api):
- branch, draft and sandbox always use the mock, so a test call never touches
  a real system;
- pre-release and live use the mock until the real API is connected and
  `settings.use_mock_api` is set to false in real-time config.

The mock keeps every payment a call makes in conv.state, so two
test calls never see each other's changes. The seed data is rebuilt from the
functions below on every read and never mutated.

Fixtures (phone, date of birth, account number):
- John Smith, 201-555-0123, 1985-03-15, 1234567890: $150.00 due in 14 days,
  Visa ending 4242 on file, a $50.00 payment already scheduled for the due date
- Jane Doe, 212-555-0178, 1990-07-22, 0987654321: $275.50 due in 10 days,
  checking account ending 6789 on file
- Alex Rivera, 201-555-0144, 1978-11-02, 2468013579: $8,400.00 due in 20 days
  (for the phone payment limit), Mastercard ending 5454 on file
- 201-555-0199: no account; 201-555-0150: flagged as a vulnerable customer
"""

import re
import uuid
from datetime import date, timedelta

from _gen import *  # <AUTO GENERATED>

LIVE_ENVS = ("pre-release", "pre_release", "live")

VULNERABLE_PHONES = {"2015550150"}


@func_description("[UTIL] Billing API client, not callable directly")
def api_client(conv: Conversation):
    return "Billing API client module."


# --- Mock or real ---------------------------------------------------------


def use_mock_api(conv) -> bool:
    if (conv.env or "").lower() not in LIVE_ENVS:
        return True
    return bool(
        (conv.real_time_config or {}).get("settings", {}).get("use_mock_api", True)
    )


def _real_api_missing(name: str):
    raise NotImplementedError(
        f"{name}: connect your billing API here, or keep settings.use_mock_api on"
    )


# --- Seed data --------------------------------------------------------------


def _today(conv=None) -> date:
    try:
        return date.fromisoformat(conv.state.today_iso)
    except (AttributeError, TypeError, ValueError):
        return date.today()


def _accounts(conv=None) -> list[dict]:
    today = _today(conv)

    def due(days: int) -> str:
        return (today + timedelta(days=days)).isoformat()

    return [
        {
            "id": "MOCK-A001",
            "first_name": "John",
            "last_name": "Smith",
            "phone": "2015550123",
            "dob": "1985-03-15",
            "member_id": "1234567890",
            "balance": 150.00,
            "due_date": due(14),
            "payment_methods": ["Visa ending 4242"],
            "scheduled_payments": [
                {"amount": 50.00, "method": "Visa ending 4242", "date": due(14)}
            ],
        },
        {
            "id": "MOCK-A002",
            "first_name": "Jane",
            "last_name": "Doe",
            "phone": "2125550178",
            "dob": "1990-07-22",
            "member_id": "0987654321",
            "balance": 275.50,
            "due_date": due(10),
            "payment_methods": ["checking account ending 6789"],
            "scheduled_payments": [],
        },
        {
            "id": "MOCK-A003",
            "first_name": "Alex",
            "last_name": "Rivera",
            "phone": "2015550144",
            "dob": "1978-11-02",
            "member_id": "2468013579",
            "balance": 8400.00,
            "due_date": due(20),
            "payment_methods": [
                "Mastercard ending 5454",
                "checking account ending 1357",
            ],
            "scheduled_payments": [],
        },
    ]


def _ledger(conv) -> dict:
    """This call's payments, kept in conv.state."""
    ledger = conv.state.mock_ledger
    if not isinstance(ledger, dict):
        ledger = {"transactions": []}
        conv.state.mock_ledger = ledger
    return ledger


def _normalise_phone(value) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def _public(account: dict) -> dict:
    """A copy of an account record; the seed data is never mutated."""
    return {
        **account,
        "payment_methods": list(account["payment_methods"]),
        "scheduled_payments": [dict(p) for p in account["scheduled_payments"]],
    }


# --- Accounts ---------------------------------------------------------------


def find_accounts_by_phone(conv, phone: str) -> list[dict]:
    """Every account on this phone number (an empty list when there is none).

    Records carry dob (YYYY-MM-DD) and member_id (the account number), which is
    what functions/idnv.py's strict check compares.
    """
    if not use_mock_api(conv):
        _real_api_missing("find_accounts_by_phone")
    digits = _normalise_phone(phone)
    return [_public(a) for a in _accounts(conv) if a["phone"] == digits]


def get_account(conv, account_id: str) -> dict | None:
    """The account with its current balance due (less this call's payments made today)
    and its scheduled payments (including any this call scheduled)."""
    if not use_mock_api(conv):
        _real_api_missing("get_account")
    account = next((a for a in _accounts(conv) if a["id"] == account_id), None)
    if account is None:
        return None
    account = _public(account)
    today = _today(conv).isoformat()
    for t in _ledger(conv)["transactions"]:
        if t["account_id"] != account_id:
            continue
        if t["date"] <= today:
            account["balance"] = round(account["balance"] - t["amount"], 2)
        else:
            account["scheduled_payments"].append(
                {"amount": t["amount"], "method": t["method"], "date": t["date"]}
            )
    return account


def is_vulnerable_caller(conv, phone: str) -> bool:
    if not use_mock_api(conv):
        _real_api_missing("is_vulnerable_caller")
    return _normalise_phone(phone) in VULNERABLE_PHONES


# --- Payments ----------------------------------------------------------------


def _confirmation_number() -> str:
    return str(uuid.uuid4().int)[:8]


def make_payment(
    conv, account_id: str, amount: float, method: str, pay_date: str
) -> dict:
    """Pay toward the balance with a payment method on file, today or on a future date.
    Returns the transaction with new_balance (the balance due once it posts)."""
    if not use_mock_api(conv):
        _real_api_missing("make_payment")
    account = get_account(conv, account_id)
    if account is None:
        raise ValueError("unknown account")
    if method not in account["payment_methods"]:
        raise ValueError("payment method not on file")
    if amount <= 0 or amount > account["balance"]:
        raise ValueError("amount not allowed")
    transaction = {
        "id": f"MOCK-T{uuid.uuid4().hex[:6].upper()}",
        "account_id": account_id,
        "amount": round(amount, 2),
        "method": method,
        "date": pay_date,
        "confirmation_number": _confirmation_number(),
    }
    ledger = _ledger(conv)
    ledger["transactions"] = ledger["transactions"] + [transaction]
    conv.state.mock_ledger = ledger
    return {**transaction, "new_balance": round(account["balance"] - amount, 2)}
