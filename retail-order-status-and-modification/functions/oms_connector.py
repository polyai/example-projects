from _gen import *  # <AUTO GENERATED>
from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse


from .narvar_client import get_shipping_status_detail


def _normalize_postal_code(raw: str) -> str:
    """Normalize a postal code -- strip spaces, uppercase, take first part before dash."""
    return raw.split("-")[0].replace(" ", "").upper()


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
    def parse_consignment_entries(
        cls, order: Any, order_line: int
    ) -> list[Consignment]:
        consignments = order.get("consignments", [])
        result = []
        for consignment in consignments:
            for entry in consignment["consignmentEntries"]:
                if entry["requestingSystemLineNo"] == str(order_line):
                    qty = next(
                        (qty for k, qty in entry.items() if k.endswith("Qty")), 0
                    )
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
                    [
                        f"{status} ({count} item(s))"
                        for status, count in status_counter.items()
                    ]
                )

            # We assume tracking_url will be the same
            shipping_order_number = next(
                (
                    qty.get_narvar_order_number()
                    for qty in self.consignments
                    if qty.tracking_url
                ),
                None,
            )
            self.narvar_order_number = shipping_order_number

        line_number = f"[OrderLine #{self.order_line_number}] "
        status = f"{('Status: ' + status_str) if status_str else ''}"

        carrier = None
        if self.consignments:
            carrier = next(
                (c.carrier_display for c in self.consignments if c.carrier_display),
                None,
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
                    self.narvar_shipment_status_code = (
                        narvar_shipping_details.status_code
                    )
                    self.narvar_shipping_status_location = (
                        narvar_shipping_details.status_location
                    )
                    self.narvar_shipment_delivery_date = (
                        narvar_shipping_details.delivery_date
                    )
                    res += narvar_shipping_details.get_line_description()
            except Exception as e:
                # Gracefully degrade if Narvar returns 404 or anything else
                conv.log.warning(
                    "narvar_integration:lookup_failed",
                    error=str(e),
                    order_line=self.order_line_number,
                    narvar_order_number=shipping_order_number,
                )

        tracking_urls = {
            c.tracking_url for c in self.consignments or [] if c.tracking_url
        }
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


def get_orders_by_phone_number(
    conv: Conversation, phone_number: str, timeout=None
) -> list[Order]:
    """Look up orders by phone number.

    Delegates to the mock/real backend returned by get_oms_api().
    Replace get_oms_api() with your OMS integration.
    """
    api = get_oms_api(conv)
    if api:
        return api.get_orders_by_phone_number(conv, phone_number, timeout=timeout)
    # No real implementation -- add your OMS integration here.
    conv.log.warning(
        "oms_connector: no backend configured for get_orders_by_phone_number"
    )
    return []


def get_order_details(
    conv: Conversation, order_number: str, timeout=None
) -> Optional[Order]:
    """Look up a single order by order number.

    Delegates to the mock/real backend returned by get_oms_api().
    Replace get_oms_api() with your OMS integration.
    """
    api = get_oms_api(conv)
    if api:
        return api.get_order_details(conv, order_number, timeout=timeout)
    # No real implementation -- add your OMS integration here.
    conv.log.warning("oms_connector: no backend configured for get_order_details")
    return None


def get_oms_api(conv):
    """Return MockOmsConnector when USE_MOCK_API is set, otherwise None.

    To integrate a real OMS, return your client object here instead of None.
    """
    if getattr(conv.state, "USE_MOCK_API", False):
        from .mock_api import get_mock_oms

        return get_mock_oms()
    return None


@func_description("Connector for OMS APIs")
def oms_connector(conv: Conversation):
    pass
