"""
Mock API for financial services template.

Provides in-memory test accounts, vulnerable customer checks, and
billing/payment operations for local development and testing when
no real backend (DynamoDB, billing API) is available.
"""

from _gen import *  # <AUTO GENERATED>
import re
import uuid
from datetime import datetime
from typing import Optional


def _normalize_phone(phone: str) -> str:
    """Strip formatting and leading US country code '1' from a phone number."""
    cleaned = re.sub(r"[\s()+-]", "", phone or "")
    # Strip leading US country code if present (11 digits starting with 1)
    if len(cleaned) == 11 and cleaned.startswith("1"):
        cleaned = cleaned[1:]
    return cleaned


# ---------------------------------------------------------------------------
# Test accounts
# ---------------------------------------------------------------------------

_ACCOUNTS: dict[str, dict] = {
    "1234567890": {
        "account_number": "1234567890",
        "name": "John Smith",
        "first_name": "John",
        "last_name": "Smith",
        "dob": "1985-03-15",
        "balance": 150.00,
        "phone": "5551234567",
        "pending_payments": [
            {
                "id": "PAY-001",
                "amount": 50.00,
                "recipient": "Electric Company",
                "scheduled_date": "2026-07-01",
                "status": "pending",
            }
        ],
        "payment_history": [
            {
                "id": "PAY-H001",
                "amount": 120.00,
                "recipient": "Water Utility",
                "date": "2026-06-15",
                "status": "completed",
                "confirmation_number": "CONF-100001",
            },
            {
                "id": "PAY-H002",
                "amount": 75.50,
                "recipient": "Internet Provider",
                "date": "2026-06-10",
                "status": "completed",
                "confirmation_number": "CONF-100002",
            },
        ],
    },
    "0987654321": {
        "account_number": "0987654321",
        "name": "Jane Doe",
        "first_name": "Jane",
        "last_name": "Doe",
        "dob": "1990-07-22",
        "balance": 275.50,
        "phone": "5559876543",
        "pending_payments": [],
        "payment_history": [
            {
                "id": "PAY-H003",
                "amount": 200.00,
                "recipient": "Rent Payment",
                "date": "2026-06-01",
                "status": "completed",
                "confirmation_number": "CONF-100003",
            },
        ],
    },
}

# Phone → account number index
_PHONE_INDEX: dict[str, str] = {
    acct["phone"]: acct_num for acct_num, acct in _ACCOUNTS.items()
}

# Confirmation number counter
_next_confirmation = 200000


# ---------------------------------------------------------------------------
# MockVulnerableCustomerCheck
# ---------------------------------------------------------------------------

# Phone numbers flagged as vulnerable
_VULNERABLE_PHONES: set[str] = {"5559991111"}


class MockVulnerableCustomerCheck:
    """In-memory vulnerable-customer phone lookup."""

    @staticmethod
    def is_vulnerable(phone_number: str) -> bool:
        """Return True if *phone_number* is flagged as vulnerable."""
        return _normalize_phone(phone_number) in _VULNERABLE_PHONES


# ---------------------------------------------------------------------------
# MockAccountLookup
# ---------------------------------------------------------------------------


class MockAccountLookup:
    """In-memory account and payment operations for testing."""

    @staticmethod
    def get_account(account_number: str) -> Optional[dict]:
        """Look up an account by number. Returns dict or None."""
        acct = _ACCOUNTS.get(account_number)
        if acct is None:
            return None
        # Return a copy so callers cannot corrupt test data across tests
        return {
            "account_number": acct["account_number"],
            "name": acct["name"],
            "first_name": acct["first_name"],
            "last_name": acct["last_name"],
            "dob": acct["dob"],
            "balance": acct["balance"],
            "phone": acct["phone"],
            "pending_payments": list(acct["pending_payments"]),
        }

    @staticmethod
    def get_account_by_phone(phone: str) -> Optional[dict]:
        """Look up an account by phone number. Returns dict or None."""
        cleaned = _normalize_phone(phone)
        acct_num = _PHONE_INDEX.get(cleaned)
        if acct_num is None:
            return None
        return MockAccountLookup.get_account(acct_num)

    @staticmethod
    def make_payment(account_number: str, amount: float) -> Optional[dict]:
        """
        Process a mock payment against *account_number*.

        Returns a dict with confirmation_number and new_balance,
        or None if the account does not exist.
        """
        global _next_confirmation
        acct = _ACCOUNTS.get(account_number)
        if acct is None:
            return None
        if amount <= 0:
            return {"error": "Payment amount must be positive"}
        if amount > acct["balance"]:
            return {"error": "Insufficient funds"}

        # Debit the account
        acct["balance"] = round(acct["balance"] - amount, 2)

        confirmation = f"CONF-{_next_confirmation}"
        _next_confirmation += 1

        # Record in history
        acct["payment_history"].append(
            {
                "id": f"PAY-{uuid.uuid4().hex[:8].upper()}",
                "amount": amount,
                "recipient": "Payment",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "status": "completed",
                "confirmation_number": confirmation,
            }
        )

        return {
            "confirmation_number": confirmation,
            "new_balance": acct["balance"],
        }

    @staticmethod
    def get_payment_history(account_number: str) -> Optional[list[dict]]:
        """
        Return payment history for *account_number*, or None if unknown.
        """
        acct = _ACCOUNTS.get(account_number)
        if acct is None:
            return None
        return list(acct["payment_history"])


# ---------------------------------------------------------------------------
# Helper: reset test data between tests
# ---------------------------------------------------------------------------


def reset_mock_data() -> None:
    """Restore all mock accounts to their original state."""
    global _next_confirmation
    _next_confirmation = 200000
    _ACCOUNTS["1234567890"]["balance"] = 150.00
    _ACCOUNTS["1234567890"]["pending_payments"] = [
        {
            "id": "PAY-001",
            "amount": 50.00,
            "recipient": "Electric Company",
            "scheduled_date": "2026-07-01",
            "status": "pending",
        }
    ]
    _ACCOUNTS["1234567890"]["payment_history"] = [
        {
            "id": "PAY-H001",
            "amount": 120.00,
            "recipient": "Water Utility",
            "date": "2026-06-15",
            "status": "completed",
            "confirmation_number": "CONF-100001",
        },
        {
            "id": "PAY-H002",
            "amount": 75.50,
            "recipient": "Internet Provider",
            "date": "2026-06-10",
            "status": "completed",
            "confirmation_number": "CONF-100002",
        },
    ]
    _ACCOUNTS["0987654321"]["balance"] = 275.50
    _ACCOUNTS["0987654321"]["pending_payments"] = []
    _ACCOUNTS["0987654321"]["payment_history"] = [
        {
            "id": "PAY-H003",
            "amount": 200.00,
            "recipient": "Rent Payment",
            "date": "2026-06-01",
            "status": "completed",
            "confirmation_number": "CONF-100003",
        },
    ]


@func_description("[UTIL] Mock financial services API for testing")
def mock_api(conv: Conversation):
    pass
