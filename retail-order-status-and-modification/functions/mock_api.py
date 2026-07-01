from datetime import datetime, timedelta
from typing import Any, Optional

from _gen import *  # <AUTO GENERATED>

from .oms_connector import Consignment, Order, OrderLine

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_NOW = datetime.now()
_THREE_DAYS = (_NOW + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
_YESTERDAY = (_NOW - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

# -- Test Customer 1: John Smith --
_CUSTOMER_1 = {
    "phone": "5550001234",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Smith",
}

_ORDER_001 = Order(
    order_number="P1032847561",
    billing_postal_code="10001",
    billing_country_code="US",
    first_name="John",
    last_name="Smith",
    email_address="john@example.com",
    account_type="REGISTERED",
    customer_id="CUST-001",
    loyalty_id="LOYALTY-001",
    order_status="FULFILMENT_COMPLETE",
    order_date_time=(_NOW - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    order_lines=[
        OrderLine(
            fulfilment_type="SHIP",
            order_line_number=1,
            ship_method="Standard Shipping",
            expected_delivery_date=_THREE_DAYS,
            product_name="Running Shoes",
            product_size="10",
            product_color="Black/White",
            product_brand="Nike",
            product_category="Footwear",
            quantity=1,
            product_sku="SKU-RS-10",
            product_code="PROD-RS-10",
            consignments=[
                Consignment(
                    shipping_status="SHIPPED",
                    cancel_reason=None,
                    tracking_url="https://tracking.example.com/track?order_number=NAR-P1032847561&carrier=UPS",
                    modified_date=(_NOW - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    carrier_display="UPS",
                ),
            ],
        ),
        OrderLine(
            fulfilment_type="SHIP",
            order_line_number=2,
            ship_method="Standard Shipping",
            expected_delivery_date=_THREE_DAYS,
            product_name="Sport Socks",
            product_size="L",
            product_color="White",
            product_brand="Nike",
            product_category="Accessories",
            quantity=1,
            product_sku="SKU-SS-L",
            product_code="PROD-SS-L",
            consignments=[
                Consignment(
                    shipping_status="SHIPPED",
                    cancel_reason=None,
                    tracking_url="https://tracking.example.com/track?order_number=NAR-P1032847561&carrier=UPS",
                    modified_date=(_NOW - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    carrier_display="UPS",
                ),
            ],
        ),
    ],
)

_ORDER_002 = Order(
    order_number="P1032891204",
    billing_postal_code="10001",
    billing_country_code="US",
    first_name="John",
    last_name="Smith",
    email_address="john@example.com",
    account_type="REGISTERED",
    customer_id="CUST-001",
    loyalty_id="LOYALTY-001",
    order_status="SUBMITTED",
    order_date_time=(_NOW - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    order_lines=[
        OrderLine(
            fulfilment_type="SHIP",
            order_line_number=1,
            ship_method="Standard Shipping",
            expected_delivery_date=(_NOW + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            product_name="Backpack",
            product_size="One Size",
            product_color="Navy",
            product_brand="Adidas",
            product_category="Accessories",
            quantity=1,
            product_sku="SKU-BP-OS",
            product_code="PROD-BP-OS",
            consignments=[
                Consignment(
                    shipping_status="CREATED",
                    cancel_reason=None,
                    tracking_url=None,
                    modified_date=None,
                    carrier_display=None,
                ),
            ],
        ),
    ],
)

# -- Test Customer 2: Jane Doe --
_CUSTOMER_2 = {
    "phone": "5550005678",
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
}

_ORDER_003 = Order(
    order_number="P1031956738",
    billing_postal_code="90210",
    billing_country_code="US",
    first_name="Jane",
    last_name="Doe",
    email_address="jane@example.com",
    account_type="GUEST",
    customer_id="CUST-002",
    loyalty_id=None,
    order_status="FULFILMENT_COMPLETE",
    order_date_time=(_NOW - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    order_lines=[
        OrderLine(
            fulfilment_type="SHIP",
            order_line_number=1,
            ship_method="Express Shipping",
            expected_delivery_date=(_NOW - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            product_name="Sneakers",
            product_size="8",
            product_color="White/Pink",
            product_brand="New Balance",
            product_category="Footwear",
            quantity=1,
            product_sku="SKU-SNK-8",
            product_code="PROD-SNK-8",
            consignments=[
                Consignment(
                    shipping_status="PICKED_BY_CUST",
                    cancel_reason=None,
                    tracking_url="https://tracking.example.com/track?order_number=NAR-P1031956738&carrier=FedEx",
                    modified_date=(_NOW - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    carrier_display="FedEx",
                ),
            ],
        ),
    ],
)

# -- Lookup indexes --
_ORDERS_BY_PHONE: dict[str, list[Order]] = {
    "5550001234": [_ORDER_001, _ORDER_002],
    "5550005678": [_ORDER_003],
}

_ORDERS_BY_NUMBER: dict[str, Order] = {
    "P1032847561": _ORDER_001,
    "P1032891204": _ORDER_002,
    "P1031956738": _ORDER_003,
}

_CUSTOMERS_BY_PHONE: dict[str, dict] = {
    "5550001234": _CUSTOMER_1,
    "5550005678": _CUSTOMER_2,
}


# ---------------------------------------------------------------------------
# MockOmsConnector
# ---------------------------------------------------------------------------


class MockOmsConnector:
    """Drop-in replacement for oms_connector functions."""

    def get_orders_by_phone_number(self, conv, phone_number: str, timeout=10) -> list[Order]:
        # Strip leading country code '1' if present
        digits = phone_number.lstrip("+").lstrip("1") if len(phone_number) > 10 else phone_number
        conv.log.info("MockOmsConnector:get_orders_by_phone_number", phone=digits)
        return list(_ORDERS_BY_PHONE.get(digits, []))

    def get_order_details(self, conv, order_number: str, timeout=10) -> Optional[Order]:
        conv.log.info("MockOmsConnector:get_order_details", order_number=order_number)
        return _ORDERS_BY_NUMBER.get(order_number)


# ---------------------------------------------------------------------------
# MockNarvarClient
# ---------------------------------------------------------------------------

# Deterministic shipping status per order
_NARVAR_SHIPPING: dict[str, dict[str, Any]] = {
    "NAR-P1032847561": {
        "status": "In Transit",
        "status_code": "300",
        "status_location": {"city": "Memphis", "state": "TN"},
        "delivery_date": _THREE_DAYS,
    },
    "NAR-P1031956738": {
        "status": "Delivered",
        "status_code": "500",
        "status_location": {"city": "Los Angeles", "state": "CA"},
        "delivery_date": _YESTERDAY,
    },
}


class MockNarvarClient:
    """Drop-in replacement for narvar_client functions."""

    def get_shipping_status_detail(
        self,
        conv,
        order_number: str,
        item: tuple[Optional[str], Optional[str]],
    ):
        """Return a NarvarShipmentDetail-like object for the given Narvar order number."""
        from .narvar_client import NarvarShipmentDetail

        conv.log.info(
            "MockNarvarClient:get_shipping_status_detail",
            order_number=order_number,
        )
        data = _NARVAR_SHIPPING.get(order_number)
        if data is None:
            return None
        return NarvarShipmentDetail(
            status=data["status"],
            status_code=data["status_code"],
            status_location=data["status_location"],
            delivery_date=data["delivery_date"],
        )


# ---------------------------------------------------------------------------
# MockZendeskClient
# ---------------------------------------------------------------------------


class MockZendeskClient:
    """Stub replacement for zendesk_client functions."""

    def search_user(self, conv, email: str):
        conv.log.info("MockZendeskClient:search_user", email=email)
        customer = next(
            (c for c in _CUSTOMERS_BY_PHONE.values() if c["email"] == email),
            None,
        )
        if customer:
            return {
                "count": 1,
                "results": [
                    {
                        "id": "MOCK-ZD-001",
                        "name": f"{customer['first_name']} {customer['last_name']}",
                        "email": customer["email"],
                    }
                ],
            }
        return {"count": 0, "results": []}

    def search_user_phone(self, conv, phone_number: str):
        conv.log.info("MockZendeskClient:search_user_phone", phone=phone_number)
        digits = phone_number.lstrip("+").lstrip("1") if len(phone_number) > 10 else phone_number
        customer = _CUSTOMERS_BY_PHONE.get(digits)
        if customer:
            return {
                "count": 1,
                "results": [
                    {
                        "id": "MOCK-ZD-001",
                        "name": f"{customer['first_name']} {customer['last_name']}",
                        "phone": phone_number,
                    }
                ],
            }
        return {"count": 0, "results": []}

    def init_zendesk_client(self, conv):
        """No-op: sets placeholder state values expected downstream."""
        conv.log.info("MockZendeskClient:init_zendesk_client")
        conv.state.zendesk_api_key = "mock-api-key"
        conv.state.zendesk_email_address = "mock@example.com"
        conv.state.zendesk_base_url = "https://mock-zendesk.example.com"

    def create_ticket(self, conv):
        """No-op: returns a fake ticket response and sets state."""
        conv.log.info("MockZendeskClient:create_ticket")
        conv.state.zendesk_ticket_id = "MOCK-TICKET-001"
        return {"ticket": {"id": "MOCK-TICKET-001", "status": "new"}}

    def update_ticket(self, conv, *args, **kwargs):
        conv.log.info("MockZendeskClient:update_ticket")
        return None

    def update_custom_fields_on_ticket(self, conv, *args, **kwargs):
        conv.log.info("MockZendeskClient:update_custom_fields_on_ticket")
        return None


# ---------------------------------------------------------------------------
# MockCustomerCoreApi
# ---------------------------------------------------------------------------


class MockCustomerCoreApi:
    """Stub replacement for customer_core_api functions."""

    def get_customers_by_phone(self, conv, phone_number: str, country_code: str = "1", timeout=10):
        digits = phone_number.lstrip("+").lstrip("1") if len(phone_number) > 10 else phone_number
        conv.log.info("MockCustomerCoreApi:get_customers_by_phone", phone=digits)
        customer = _CUSTOMERS_BY_PHONE.get(digits)
        if customer:
            return {"results": [{"email": customer["email"]}]}
        return {"results": []}

    def get_email_by_phone(self, conv, phone_number: str, timeout=10) -> Optional[str]:
        digits = phone_number.lstrip("+").lstrip("1") if len(phone_number) > 10 else phone_number
        conv.log.info("MockCustomerCoreApi:get_email_by_phone", phone=digits)
        customer = _CUSTOMERS_BY_PHONE.get(digits)
        return customer["email"] if customer else None


# ---------------------------------------------------------------------------
# Singleton instances (used by factory functions)
# ---------------------------------------------------------------------------

_mock_oms = MockOmsConnector()
_mock_narvar = MockNarvarClient()
_mock_zendesk = MockZendeskClient()
_mock_customer = MockCustomerCoreApi()


def get_mock_oms() -> MockOmsConnector:
    return _mock_oms


def get_mock_narvar() -> MockNarvarClient:
    return _mock_narvar


def get_mock_zendesk() -> MockZendeskClient:
    return _mock_zendesk


def get_mock_customer() -> MockCustomerCoreApi:
    return _mock_customer


@func_description("Mock API implementations for local testing")
def mock_api(conv: Conversation):
    pass
