"""Tests for the retail mock APIs — verifies in-memory order/shipping/customer data."""

from unittest.mock import MagicMock

import pytest
from functions.mock_api import (
    MockCustomerCoreApi,
    MockNarvarClient,
    MockOmsConnector,
    MockZendeskClient,
)


@pytest.fixture
def conv():
    return MagicMock()


@pytest.fixture
def oms(conv):
    return MockOmsConnector()


@pytest.fixture
def narvar(conv):
    return MockNarvarClient()


@pytest.fixture
def zendesk(conv):
    return MockZendeskClient()


@pytest.fixture
def customer_api(conv):
    return MockCustomerCoreApi()


class TestOmsConnector:
    def test_orders_by_known_phone(self, oms, conv):
        orders = oms.get_orders_by_phone_number(conv, "5550001234")
        assert len(orders) >= 1

    def test_orders_by_unknown_phone(self, oms, conv):
        orders = oms.get_orders_by_phone_number(conv, "0000000000")
        assert len(orders) == 0

    def test_order_details_known(self, oms, conv):
        order = oms.get_order_details(conv, "P1032847561")
        assert order is not None

    def test_order_details_unknown(self, oms, conv):
        order = oms.get_order_details(conv, "NONEXISTENT")
        assert order is None


class TestNarvarClient:
    def test_shipped_order_tracking(self, narvar, conv):
        result = narvar.get_shipping_status_detail(
            conv, order_number="NAR-P1032847561", item=("ITEM-001", "Running Shoes")
        )
        assert result is not None


class TestZendeskClient:
    def test_search_user_by_email(self, zendesk, conv):
        result = zendesk.search_user(conv, "john@example.com")
        assert result["count"] >= 1

    def test_search_user_unknown(self, zendesk, conv):
        result = zendesk.search_user(conv, "unknown@example.com")
        assert result["count"] == 0

    def test_update_ticket_noop(self, zendesk, conv):
        zendesk.update_ticket(conv, "MOCK-TICKET", "solved", "test comment")


class TestCustomerCoreApi:
    def test_email_by_known_phone(self, customer_api, conv):
        email = customer_api.get_email_by_phone(conv, "5550001234")
        assert email == "john@example.com"

    def test_email_by_unknown_phone(self, customer_api, conv):
        email = customer_api.get_email_by_phone(conv, "0000000000")
        assert email is None

    def test_customers_by_phone(self, customer_api, conv):
        result = customer_api.get_customers_by_phone(conv, "5550005678")
        assert result is not None
