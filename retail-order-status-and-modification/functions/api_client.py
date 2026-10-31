"""Order system client: customers, orders, shipment tracking, cancellations and
delivery address changes.

Every tool reads and writes through this module, so connecting a real order
management system (and carrier tracking) means replacing the bodies of the
helpers below and nothing else.

Mock or real (see use_mock_api):
- branch, draft and sandbox always use the mock, so a test call never touches
  a real system;
- pre-release and live use the mock until the real API is connected and
  `settings.use_mock_api` is set to false in real-time config.

The mock keeps every change a call makes (cancellations, address changes) in
conv.state, so two test calls never see each other's changes. The seed data is
rebuilt from the functions below on every read and never mutated.

Fixtures (dates are relative to the day of the call):
- John Smith, 201-555-0123
    P1032847561 (ending 7561): Nike Running Shoes size 10 + Nike Sport Socks,
        shipped with UPS, in transit, arriving in 3 days
    P1032891204 (ending 1204): Adidas Backpack, still processing (can be
        cancelled, delivery address can be changed)
- Jane Doe, 212-555-0178
    P1031956738 (ending 6738): New Balance Sneakers size 8, delivered a week ago
- Maria Garcia, 310-555-0142
    P1033012345 (ending 2345): Champion Hoodie cancelled (out of stock) + Hydro
        Water Bottle shipped with FedEx, arriving in 2 days
    P1033019876 (ending 9876): New Era Cap, ready to pick up in store
    P1033020000 (ending 0000): on hold for review (a colleague has to help)
- 201-555-0199: no account
"""

import re
from datetime import date, timedelta

from _gen import *  # <AUTO GENERATED>

LIVE_ENVS = ("pre-release", "pre_release", "live")

# Item statuses the tools understand.
PROCESSING = "processing"
SHIPPED = "shipped"
DELIVERED = "delivered"
READY_FOR_PICKUP = "ready_for_pickup"
PICKED_UP = "picked_up"
CANCELLED = "cancelled"


@func_description("[UTIL] Order system API client, not callable directly")
def api_client(conv: Conversation):
    return "Order system API client module."


# --- Mock or real ---------------------------------------------------------


def use_mock_api(conv) -> bool:
    if (conv.env or "").lower() not in LIVE_ENVS:
        return True
    return bool(
        (conv.real_time_config or {}).get("settings", {}).get("use_mock_api", True)
    )


def _real_api_missing(name: str):
    raise NotImplementedError(
        f"{name}: connect your order system here, or keep settings.use_mock_api on"
    )


# --- Seed data --------------------------------------------------------------


def _today(conv=None) -> date:
    try:
        return date.fromisoformat(conv.state.today_iso)
    except (AttributeError, TypeError, ValueError):
        return date.today()


def _customers() -> list[dict]:
    return [
        {
            "id": "CUST-001",
            "first_name": "John",
            "last_name": "Smith",
            "phone": "2015550123",
        },
        {
            "id": "CUST-002",
            "first_name": "Jane",
            "last_name": "Doe",
            "phone": "2125550178",
        },
        {
            "id": "CUST-003",
            "first_name": "Maria",
            "last_name": "Garcia",
            "phone": "3105550142",
        },
    ]


def _item(
    name, brand, category, size="", quantity=1, status=PROCESSING, **shipment
) -> dict:
    return {
        "name": name,
        "brand": brand,
        "category": category,
        "size": size,
        "quantity": quantity,
        "status": status,
        "cancel_reason": shipment.get("cancel_reason", ""),
        "carrier": shipment.get("carrier", ""),
        "tracking_status": shipment.get("tracking_status", ""),
        "last_scan": shipment.get("last_scan", ""),
        "tracking_url": shipment.get("tracking_url", ""),
        "expected_delivery": shipment.get("expected_delivery", ""),
        "completed_on": shipment.get("completed_on", ""),
    }


def _seed_orders(conv=None) -> list[dict]:
    today = _today(conv)

    def day(offset: int) -> str:
        return (today + timedelta(days=offset)).isoformat()

    home = "100 Main Street, New York, NY 10001"
    return [
        {
            "order_number": "P1032847561",
            "customer_id": "CUST-001",
            "placed": day(-5),
            "fulfilment": "ship",
            "hold": "",
            "shipping_address": home,
            "items": [
                _item(
                    "Running Shoes", "Nike", "Footwear", "10", status=SHIPPED, carrier="UPS",
                    tracking_status="in transit", last_scan="Memphis, Tennessee",
                    expected_delivery=day(3),
                    tracking_url="https://tracking.example.com/track?order=P1032847561&carrier=UPS",
                ),
                _item(
                    "Sport Socks", "Nike", "Accessories", "L", status=SHIPPED, carrier="UPS",
                    tracking_status="in transit", last_scan="Memphis, Tennessee",
                    expected_delivery=day(3),
                    tracking_url="https://tracking.example.com/track?order=P1032847561&carrier=UPS",
                ),
            ],
        },
        {
            "order_number": "P1032891204",
            "customer_id": "CUST-001",
            "placed": day(-1),
            "fulfilment": "ship",
            "hold": "",
            "shipping_address": home,
            "items": [_item("Backpack", "Adidas", "Accessories", "One Size")],
        },
        {
            "order_number": "P1031956738",
            "customer_id": "CUST-002",
            "placed": day(-10),
            "fulfilment": "ship",
            "hold": "",
            "shipping_address": "22 Ocean Avenue, Los Angeles, CA 90210",
            "items": [
                _item(
                    "Sneakers", "New Balance", "Footwear", "8", status=DELIVERED,
                    carrier="FedEx", completed_on=day(-7),
                    tracking_url="https://tracking.example.com/track?order=P1031956738&carrier=FedEx",
                )
            ],
        },
        {
            "order_number": "P1033012345",
            "customer_id": "CUST-003",
            "placed": day(-3),
            "fulfilment": "ship",
            "hold": "",
            "shipping_address": "8 Palm Drive, Santa Monica, CA 90401",
            "items": [
                _item("Hoodie", "Champion", "Clothing", "M", status=CANCELLED, cancel_reason="out_of_stock"),
                _item(
                    "Water Bottle", "Hydro", "Accessories", status=SHIPPED, carrier="FedEx",
                    tracking_status="in transit", last_scan="Phoenix, Arizona",
                    expected_delivery=day(2),
                    tracking_url="https://tracking.example.com/track?order=P1033012345&carrier=FedEx",
                ),
            ],
        },
        {
            "order_number": "P1033019876",
            "customer_id": "CUST-003",
            "placed": day(-2),
            "fulfilment": "pickup",
            "hold": "",
            "shipping_address": "",
            "items": [_item("Cap", "New Era", "Accessories", status=READY_FOR_PICKUP)],
        },
        {
            "order_number": "P1033020000",
            "customer_id": "CUST-003",
            "placed": day(-1),
            "fulfilment": "ship",
            "hold": "review",
            "shipping_address": "8 Palm Drive, Santa Monica, CA 90401",
            "items": [_item("Jacket", "North Face", "Clothing", "M")],
        },
    ]  # fmt: skip


def _changes(conv) -> dict:
    """This call's cancellations and address changes, kept in conv.state."""
    changes = conv.state.mock_changes
    if not isinstance(changes, dict):
        changes = {"cancelled": [], "addresses": {}}
        conv.state.mock_changes = changes
    return changes


def _normalise_phone(value) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def _apply_changes(conv, order: dict) -> dict:
    changes = _changes(conv)
    order = {**order, "items": [dict(i) for i in order["items"]]}
    if order["order_number"] in changes["cancelled"]:
        for item in order["items"]:
            item["status"] = CANCELLED
            item["cancel_reason"] = "customer_request"
    if order["order_number"] in changes["addresses"]:
        order["shipping_address"] = changes["addresses"][order["order_number"]]
    return order


# --- Customers --------------------------------------------------------------


def find_customers_by_phone(conv, phone: str) -> list[dict]:
    """Every account on this phone number (an empty list when there is none)."""
    if not use_mock_api(conv):
        _real_api_missing("find_customers_by_phone")
    digits = _normalise_phone(phone)
    return [dict(c) for c in _customers() if c["phone"] == digits]


# --- Orders -----------------------------------------------------------------


def list_orders(conv, customer_id: str) -> list[dict]:
    """A customer's recent orders, newest first."""
    if not use_mock_api(conv):
        _real_api_missing("list_orders")
    orders = [
        _apply_changes(conv, o)
        for o in _seed_orders(conv)
        if o["customer_id"] == customer_id
    ]
    return sorted(orders, key=lambda o: o["placed"], reverse=True)


def cancel_order(conv, order_number: str, reason: str) -> bool:
    if not use_mock_api(conv):
        _real_api_missing("cancel_order")
    changes = _changes(conv)
    changes["cancelled"] = changes["cancelled"] + [order_number]
    conv.state.mock_changes = changes
    conv.log.info("Mock cancellation", order_number=order_number, reason=reason)
    return True


def update_delivery_address(conv, order_number: str, address: str) -> bool:
    if not use_mock_api(conv):
        _real_api_missing("update_delivery_address")
    changes = _changes(conv)
    changes["addresses"] = {**changes["addresses"], order_number: address}
    conv.state.mock_changes = changes
    conv.log.info("Mock address change", order_number=order_number)
    return True
