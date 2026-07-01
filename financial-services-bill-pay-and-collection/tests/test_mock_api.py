"""Tests for the financial services mock API."""

import sys
import types
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: make _gen and functions importable outside Agent Studio
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(_PROJECT_ROOT))

# Stub out _gen so decorated functions are importable
_fake_gen = types.ModuleType("_gen")
_fake_gen.func_description = lambda *a, **kw: lambda fn: fn
_fake_gen.func_parameter = lambda *a, **kw: lambda fn: fn
_fake_gen.func_latency_control = lambda *a, **kw: lambda fn: fn
_fake_gen.Conversation = type("Conversation", (), {})
sys.modules.setdefault("_gen", _fake_gen)

# Ensure `functions` is a package pointing at the project's functions dir
_functions_dir = _PROJECT_ROOT / "functions"
_functions_pkg = types.ModuleType("functions")
_functions_pkg.__path__ = [str(_functions_dir)]
_functions_pkg.__package__ = "functions"
sys.modules.setdefault("functions", _functions_pkg)

from functions.mock_api import (  # noqa: E402
    MockAccountLookup,
    MockVulnerableCustomerCheck,
    reset_mock_data,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset():
    """Reset mock data before each test to prevent cross-test pollution."""
    reset_mock_data()


# ---------------------------------------------------------------------------
# Account lookup by number
# ---------------------------------------------------------------------------


class TestGetAccount:
    def test_known_account_john(self):
        acct = MockAccountLookup.get_account("1234567890")
        assert acct is not None
        assert acct["name"] == "John Smith"
        assert acct["balance"] == 150.00
        assert acct["dob"] == "1985-03-15"
        assert len(acct["pending_payments"]) == 1

    def test_known_account_jane(self):
        acct = MockAccountLookup.get_account("0987654321")
        assert acct is not None
        assert acct["name"] == "Jane Doe"
        assert acct["balance"] == 275.50
        assert acct["dob"] == "1990-07-22"
        assert acct["pending_payments"] == []

    def test_unknown_account_returns_none(self):
        assert MockAccountLookup.get_account("0000000000") is None

    def test_returns_copy_not_reference(self):
        """Mutating the returned dict must not corrupt the source data."""
        acct = MockAccountLookup.get_account("1234567890")
        assert acct is not None
        acct["balance"] = 0
        fresh = MockAccountLookup.get_account("1234567890")
        assert fresh is not None
        assert fresh["balance"] == 150.00


# ---------------------------------------------------------------------------
# Account lookup by phone
# ---------------------------------------------------------------------------


class TestGetAccountByPhone:
    def test_known_phone(self):
        acct = MockAccountLookup.get_account_by_phone("5551234567")
        assert acct is not None
        assert acct["account_number"] == "1234567890"

    def test_known_phone_with_formatting(self):
        acct = MockAccountLookup.get_account_by_phone("+1 (555) 123-4567")
        assert acct is not None
        assert acct["account_number"] == "1234567890"

    def test_unknown_phone_returns_none(self):
        assert MockAccountLookup.get_account_by_phone("0000000000") is None

    def test_empty_phone_returns_none(self):
        assert MockAccountLookup.get_account_by_phone("") is None


# ---------------------------------------------------------------------------
# Make payment
# ---------------------------------------------------------------------------


class TestMakePayment:
    def test_successful_payment(self):
        result = MockAccountLookup.make_payment("1234567890", 50.00)
        assert result is not None
        assert "confirmation_number" in result
        assert result["confirmation_number"].startswith("CONF-")
        assert result["new_balance"] == 100.00

    def test_payment_updates_balance(self):
        MockAccountLookup.make_payment("1234567890", 30.00)
        acct = MockAccountLookup.get_account("1234567890")
        assert acct is not None
        assert acct["balance"] == 120.00

    def test_payment_unknown_account(self):
        assert MockAccountLookup.make_payment("0000000000", 10.00) is None

    def test_payment_insufficient_funds(self):
        result = MockAccountLookup.make_payment("1234567890", 999.00)
        assert result is not None
        assert result.get("error") == "Insufficient funds"

    def test_payment_zero_amount(self):
        result = MockAccountLookup.make_payment("1234567890", 0)
        assert result is not None
        assert result.get("error") == "Payment amount must be positive"

    def test_payment_negative_amount(self):
        result = MockAccountLookup.make_payment("1234567890", -10.00)
        assert result is not None
        assert result.get("error") == "Payment amount must be positive"

    def test_multiple_payments_sequential(self):
        r1 = MockAccountLookup.make_payment("1234567890", 50.00)
        r2 = MockAccountLookup.make_payment("1234567890", 50.00)
        assert r1 is not None
        assert r2 is not None
        assert r1["confirmation_number"] != r2["confirmation_number"]
        assert r2["new_balance"] == 50.00


# ---------------------------------------------------------------------------
# Payment history
# ---------------------------------------------------------------------------


class TestPaymentHistory:
    def test_history_known_account(self):
        history = MockAccountLookup.get_payment_history("1234567890")
        assert history is not None
        assert len(history) == 2
        assert all("confirmation_number" in h for h in history)

    def test_history_after_payment(self):
        MockAccountLookup.make_payment("1234567890", 10.00)
        history = MockAccountLookup.get_payment_history("1234567890")
        assert len(history) == 3

    def test_history_unknown_account(self):
        assert MockAccountLookup.get_payment_history("0000000000") is None


# ---------------------------------------------------------------------------
# Vulnerable customer check
# ---------------------------------------------------------------------------


class TestVulnerableCustomerCheck:
    def test_flagged_phone(self):
        assert MockVulnerableCustomerCheck.is_vulnerable("5559991111") is True

    def test_flagged_phone_with_formatting(self):
        assert MockVulnerableCustomerCheck.is_vulnerable("+1 (555) 999-1111") is True

    def test_non_flagged_phone(self):
        assert MockVulnerableCustomerCheck.is_vulnerable("5551234567") is False

    def test_empty_phone(self):
        assert MockVulnerableCustomerCheck.is_vulnerable("") is False

    def test_none_phone(self):
        assert MockVulnerableCustomerCheck.is_vulnerable(None) is False
