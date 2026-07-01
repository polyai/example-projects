from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import requests
from _gen import *  # <AUTO GENERATED>
from utils.secret_vault import secret_vault

from .narvar_client import get_shipping_status_detail


def _normalize_postal_code(raw: str) -> str:
    """Normalize a postal code — strip spaces, uppercase, take first part before dash."""
    return raw.split("-")[0].replace(" ", "").upper()


def _banner_id_for(conv) -> Optional[int]:
    brand = conv.state.brand
    if brand == "Poly Store":
        return 1
    return None


@dataclass
class Consignment:
    shipping_status: Optional[str]
    cancel_reason: Optional[str]
    tracking_url: Optional[str]
    modified_date: Optional[str]
    carrier_display: Optional[str]

    def get_narvar_order_number(self) -> Optional[str]:
        if self.tracking_url is None:
            return None

        parsed_url = urlparse(self.tracking_url)
        query_params = parse_qs(parsed_url.query)
        return query_params.get("order_number", [None])[0]


@dataclass
class OrderLine:
    fulfilment_type: str
    order_line_number: int
    ship_method: str
    expected_delivery_date: Optional[str]
    product_name: str
    product_size: str
    product_color: str
    product_brand: str
    product_category: str
    quantity: int
    product_sku: Optional[str]
    product_code: Optional[str]
    consignments: Optional[list[Consignment]]
    narvar_order_number: Optional[str] = None
    narvar_shipping_status: Optional[str] = None
    narvar_shipment_status_code: Optional[str] = None
    narvar_shipment_status_location: Optional[dict[str, str]] = None
    narvar_shipment_delivery_date: Optional[str] = None

    def __getitem__(self, item):
        return getattr(self, item)

    @classmethod
    def parse_consignment_entries(cls, order: Any, order_line: int) -> list[Consignment]:
        consignments = order.get("consignments", [])
        result = []
        for consignment in consignments:
            for entry in consignment["consignmentEntries"]:
                if entry["requestingSystemLineNo"] == str(order_line):
                    qty = next((qty for k, qty in entry.items() if k.endswith("Qty")), 0)
                    for _ in range(qty):
                        result.append(
                            Consignment(
                                entry.get("entryStatus", None),
                                entry.get("cancelCode", None),
                                entry.get("trackingUrl", None),
                                entry.get("modifiedDate", None),
                                entry.get("carrierDisplay", None),
                            )
                        )
        return result

    def line_description(self, conv, include_line_number=True, include_status=True):
        status_str = None
        shipping_order_number = None
        if self.consignments:
            status_counter = Counter(
                f"{consignment.shipping_status}"
                f"{'- ' + consignment.cancel_reason if consignment.cancel_reason else ''}"
                for consignment in self.consignments
            )

            if len(status_counter.keys()) == 1:
                status_str = next(status_counter.elements())
            else:
                status_str = ", ".join(
                    [f"{status} ({count} item(s))" for status, count in status_counter.items()]
                )

            # We assume tracking_url will be the same
            shipping_order_number = next(
                (qty.get_narvar_order_number() for qty in self.consignments if qty.tracking_url),
                None,
            )
            self.narvar_order_number = shipping_order_number

        line_number = f"[OrderLine #{self.order_line_number}] "
        status = f"{('Status: ' + status_str) if status_str else ''}"

        carrier = None
        if self.consignments:
            carrier = next(
                (c.carrier_display for c in self.consignments if c.carrier_display), None
            )

        res = (
            f"{line_number if include_line_number else ''}"
            f"{self.product_name} "
            f"(Size {self.product_size}, {self.product_color}) in "
            f"{self.product_category} category. "
            f"Quantity: {self.quantity}. "
            f"Fulfillment Type: {self.fulfilment_type}. "
            f"{status if include_status else ''}. "
            f"{f'Carrier: {carrier}. ' if carrier else ''}"
        )
        conv.log.info(
            "narvar_integration:if_block_check",
            conv_exists=bool(conv),
            has_shipping_order_number=bool(shipping_order_number),
            env=conv.env,
            order_line=self.order_line_number,
        )
        # change condition for testing narvar integration
        if (
            conv
            and shipping_order_number
            and (conv.env in ("live", "pre-release", "draft", "sandbox"))
        ):
            try:
                narvar_shipping_details = get_shipping_status_detail(
                    conv, shipping_order_number, (self.product_code, self.product_sku)
                )
                if narvar_shipping_details:
                    self.narvar_shipping_status = narvar_shipping_details.status
                    self.narvar_shipment_status_code = narvar_shipping_details.status_code
                    self.narvar_shipping_status_location = narvar_shipping_details.status_location
                    self.narvar_shipment_delivery_date = narvar_shipping_details.delivery_date
                    res += narvar_shipping_details.get_line_description()
            except Exception as e:
                # Gracefully degrade if Narvar returns 404 or anything else
                conv.log.warning(
                    "narvar_integration:lookup_failed",
                    error=str(e),
                    order_line=self.order_line_number,
                    narvar_order_number=shipping_order_number,
                )

        tracking_urls = {c.tracking_url for c in self.consignments or [] if c.tracking_url}
        conv.log.info(
            "line_description:tracking_urls",
            order_line=self.order_line_number,
            urls=list(tracking_urls),
        )
        for url in tracking_urls:
            res += f" Tracking_URL: {url}"

        return res


@dataclass
class Order:
    order_number: str
    billing_postal_code: str
    billing_country_code: str
    first_name: str
    last_name: str
    email_address: str
    account_type: str
    customer_id: str
    loyalty_id: Optional[str]
    order_status: str
    order_lines: list[OrderLine]
    order_date_time: Optional[str] = None

    def __getitem__(self, item):
        return getattr(self, item)


def _parse_order_details(order: Any) -> Order:
    return Order(
        order["order"]["orderStatus"].get("orderNumber")
        or order["order"]["orderRequest"]["flRequestId"],
        _normalize_postal_code(order["order"]["orderHeader"]["billingAddress"]["postalCode"]),
        order["order"]["orderHeader"]["billingAddress"].get("countryCode", "US"),
        order["order"]["user"]["firstName"],
        order["order"]["user"]["lastName"],
        order["order"]["user"]["email"],
        order["order"]["user"]["type"],
        order["order"]["user"]["id"],
        order["order"]["user"].get("loyaltyId", None),
        order["order"]["orderStatus"]["orderStatus"],
        [
            OrderLine(
                group["fullfillmentType"],
                line["lineNumber"],
                line["shipMethodDesc"],
                line.get("expectedDeliveryDate", None),
                line["product"]["name"],
                line["product"]["size"],
                line["product"]["color"],
                line["product"]["brand"],
                line["product"].get("category", None),
                line["quantity"],
                line["product"]["sku"],
                line["product"]["productNumber"],
                OrderLine.parse_consignment_entries(order["order"], line["lineNumber"]) or [],
            )
            for group in order["order"]["fullfillmentGrouping"]
            for line in group["orderLines"]
        ],
        order["order"]["orderHeader"].get("orderDateTime", None),
    )


def get_orders_by_phone_number(conv: Conversation, phone_number: str, timeout=None) -> list[Order]:
    """Get orders by phone number. Delegates to MAO SearchV2 when USE_MAO_API flag is set.

    When USE_MAO_API is set, tries MAO first. If no results found and we're in the
    transition window, falls back to the legacy OMS/Apigee API for historical orders.
    """
    mock = get_oms_api(conv)
    if mock:
        return mock.get_orders_by_phone_number(conv, phone_number, timeout=timeout)

    return _get_orders_by_phone_legacy(conv, phone_number, timeout=timeout)


def _get_orders_by_phone_legacy(conv: Conversation, phone_number: str, timeout=None) -> list[Order]:
    """Get orders by phone number via legacy OMS/Apigee API."""
    banner_id = _banner_id_for(conv)
    if banner_id is None:
        conv.log.error("OMS legacy: unknown brand for phone lookup", brand=conv.state.brand)
        return []

    conv.log.info("OMS legacy: phone search", banner_id=banner_id)
    resp = _make_request(
        conv,
        "GET",
        f"orders/banners/{banner_id}/orders/?phone={phone_number}",
        None,
        timeout=timeout,
    )
    conv.log.info("OMS legacy: phone search result", order_count=len(resp))
    return [_parse_order_details(order) for order in resp]


def get_orders_by_email(conv: Conversation, email: str, timeout=None) -> list[Order]:
    """Get orders by email"""
    banner_id = _banner_id_for(conv)
    if banner_id is None:
        conv.log.error("OMS: unknown brand for email lookup", brand=conv.state.brand)
        return []

    resp = _make_request(
        conv,
        "GET",
        f"orders/banners/{banner_id}/orders/?email={email}",
        None,
        timeout=timeout,
    )
    return [_parse_order_details(order) for order in resp]


def get_order_details(conv: Conversation, order_number: str, timeout=None) -> Optional[Order]:
    """Get order by order number. Delegates to MAO when USE_MAO_API flag is set.

    When USE_MAO_API is set, tries MAO Order API first (full detail with tracking).
    Falls back to legacy OMS for historical orders during transition.
    """
    mock = get_oms_api(conv)
    if mock:
        return mock.get_order_details(conv, order_number, timeout=timeout)

    return _get_order_details_legacy(conv, order_number, timeout=timeout)


def _get_order_details_legacy(
    conv: Conversation, order_number: str, timeout=None
) -> Optional[Order]:
    """Get order by order number via legacy OMS/Apigee API."""
    conv.log.info("OMS legacy: order lookup", order_number=order_number)
    resp = _make_request(conv, "GET", f"orders/{order_number}", None, timeout=timeout)

    if "errors" in resp:
        conv.log.info("OMS legacy: order not found", order_number=order_number)
        return None

    order = _parse_order_details(resp)
    conv.log.info(
        "OMS legacy: order found",
        order_number=order.order_number,
        order_status=order.order_status,
    )
    return order


def _make_request(
    conv: Conversation,
    http_method: str,
    endpoint: str,
    payload: Optional[dict[str, Any]],
    timeout: Optional[int] = None,
):
    vault_name = "oms_mock_api" if conv.state.OMS_API_USE_MOCK else "oms_api"
    vault = secret_vault(vault_name)
    if conv.real_time_config.get("oms_api_env") == "prod" or conv.env == "live":
        vault = secret_vault("oms_prod_api")
    x_api_key = vault.get("API_KEY")
    base_url = vault.get("BASE_URL")

    headers = {"Content-Type": "application/json", "X-API-KEY": x_api_key}

    full_url = f"{base_url}/{endpoint}"
    conv.log.info(
        "OMS legacy: request",
        http_method=http_method,
        url=full_url,
        vault=vault_name,
        timeout=timeout,
    )
    response = requests.request(
        method=http_method, url=full_url, headers=headers, json=payload, timeout=timeout
    )
    try:
        response_data = response.json()
    except ValueError:
        response_data = response.text

    if response.status_code not in [200, 404]:
        conv.log.error(
            "OMS legacy: request error",
            status_code=response.status_code,
            url=full_url,
            http_method=http_method,
            response=response_data,
        )
    else:
        conv.log.info(
            "OMS legacy: request complete",
            status_code=response.status_code,
            url=full_url,
            response=response_data,
        )

    response.raise_for_status()
    return response_data


def get_oms_api(conv):
    """Return MockOmsConnector when USE_MOCK_API is set, otherwise None (use module functions directly)."""
    if getattr(conv.state, "USE_MOCK_API", False):
        from .mock_api import get_mock_oms

        return get_mock_oms()
    return None


@func_description(
    "Connector for OMS APIs. It's used to for OMS operations such as retrieving order details."
)
@func_parameter("phone_number", "phone number")
def oms_connector(conv: Conversation, phone_number: str):
    # Add your function definition here.
    # You can optionally return a string that will be fed back to the LLM.
    resp = get_order_details(conv, phone_number)
    if resp is not None:
        for order in resp.order_lines:
            print(order.line_description(conv))
    return str(resp)
