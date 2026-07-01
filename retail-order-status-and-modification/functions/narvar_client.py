import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlencode, urljoin

import requests
from _gen import *  # <AUTO GENERATED>
from utils.secret_vault import secret_vault

# NARVAR STATUS CODES
# https://docs.google.com/spreadsheets/d/10U4vzXWT9ClPtgL_QGLv5lFTKbUKhf8K/edit?gid=1350376284#gid=1350376284

STATUS_CODE_DESCRIPTION = {
    "000": "Internal",
    "100": "About to ship",
    "101": "About to ship",
    "200": "Just shipped",
    "208": "Just shipped",
    "290": "Just shipped",
    "293": "Just shipped",
    "300": "In transit",
    "301": "In transit",
    "302": "In transit",
    "303": "In transit",
    "304": "In transit",
    "305": "In transit",
    "306": "In transit",
    "307": "In transit",
    "308": "In transit",
    "310": "In transit",
    "315": "In transit",
    "319": "In transit",
    "320": "In transit",
    "321": "In transit",
    "322": "In transit",
    "323": "In transit",
    "400": "Out for delivery",
    "401": "Out for delivery tomorrow",
    "500": "Delivered",
    "501": "Delivered",
    "502": "Delivered to a pickup point",
    "503": "Picked up",
    "600": "Delayed",
    "601": "Delayed",
    "602": "Delayed",
    "603": "Delayed",
    "604": "Delayed",
    "605": "Delayed",
    "607": "Delayed",
    "608": "Delayed",
    "609": "Delayed",
}

HANDOFF_STATUS_CODE = [
    "700",
    "701",
    "702",
    "703",
    "704",
    "705",
    "706",
    "708",
    "709",
    "710",
    "711",
    "800",
    "801",
    "802",
    "803",
    "900",
]
# Include extended exception codes from "804" to "820"
HANDOFF_STATUS_CODE.extend([str(code) for code in range(804, 821)])


def _load_api_config(conv: Conversation) -> tuple[str, str, str]:
    """Load API config from secret vault.

    Returns:
      Tuple of (api_key, email_address, base_url)
    """
    brand = conv.state.brand
    if not brand:
        brand = "Poly Store"

    if conv.env in ("live", "draft", "pre-release"):
        secret_name = "narvar_production_api"
    else:
        # TODO: add staging secret names once available
        secret_name = "narvar_staging_api"

    token = secret_vault(secret_name)

    return token["HMAC"], token["RETAILER_MONIKER"], token["BASE_URL"]


def _make_request(
    conv: Conversation, http_method: str, url: str, payload: Optional[dict[str, Any]]
):
    headers = {
        "Content-Type": "application/json",
    }

    response = requests.request(
        method=http_method,
        url=url,
        headers=headers,
        json=payload,
    )

    if response.status_code != 200:
        conv.log.error(
            "NARVAR API _make_request error", response=response.json(), url=url, payload=payload
        )
    else:
        conv.log.info("_make_request response", response=response.json(), url=url, payload=payload)

    response.raise_for_status()
    return response.json()


def track_by_order_number(conv: Conversation, order_number: str, tiemout=None) -> dict[str, Any]:
    hmac_key, retailer_moniker, base_url = _load_api_config(conv)
    epoch = round(time.time())
    epoch_token = hmac.new(hmac_key.encode(), str(epoch).encode(), hashlib.sha256).hexdigest()
    order_token = hmac.new(
        hmac_key.encode(), f"{order_number}:{epoch}".encode(), hashlib.sha256
    ).hexdigest()

    base_path = f"/api/v2/orders/{order_number}/tracking"
    query_params = {
        "retailer_moniker": retailer_moniker,
        "order_token": order_token,
        "epoch": epoch,
        "epoch_token": epoch_token,
    }

    full_url = urljoin(base_url, base_path) + "?" + urlencode(query_params)
    resp = _make_request(conv, "GET", full_url, None)
    if "errors" in resp:
        conv.log.warning(
            "NARVAR api response contains error", response=resp, order_number=order_number
        )
        return {}

    return resp


@dataclass
class NarvarShipmentDetail:
    status: str
    status_code: str
    status_location: dict[str, str]
    delivery_date: str

    def get_line_description(self) -> str:
        shipment_status = STATUS_CODE_DESCRIPTION.get(self.status_code)

        city = state = ""
        if self.status_location and shipment_status == "In transit":
            city = self.status_location.get("city") or ""
            state = self.status_location.get("state") or ""

        return (
            (f"Shipment_Status: {shipment_status}. " if shipment_status else "")
            + (f"Delivery_Date: {self.delivery_date}. " if self.delivery_date else "")
            + (f"Shipment_Location: {city}, {state}." if city or state else "")
        )


def get_shipping_status_detail(
    conv: Conversation, order_number: str, item: tuple[Optional[str], Optional[str]]
) -> Optional[NarvarShipmentDetail]:
    """
    Get the line description of the order's shipping status.

    order_number: Narvar order number
    item: (item_id, sku)
    """
    mock = get_narvar_api(conv)
    if mock:
        return mock.get_shipping_status_detail(conv, order_number, item)

    if (
        conv.state.shipping_order_number_caches
        and order_number in conv.state.shipping_order_number_caches
    ):
        shipping_information = conv.state.shipping_order_number_caches[order_number]
    else:
        shipping_information = track_by_order_number(conv, order_number)
        if conv.state.shipping_order_number_caches is None:
            conv.state.shipping_order_number_caches = {}
        conv.state.shipping_order_number_caches[order_number] = shipping_information

    item_shipment = None
    shipments = shipping_information.get("order_info", {}).get("shipments", [])

    # Try matching product_code → Narvar item_id, then product_sku → Narvar sku
    for shipment in shipments:
        if item[0] and any(i.get("item_id") == item[0] for i in shipment.get("items_info", [])):
            item_shipment = shipment
            break
    else:
        for shipment in shipments:
            if item[1] and any(i.get("sku") == item[1] for i in shipment.get("items_info", [])):
                item_shipment = shipment
                break

    # Cross-match: product_sku → Narvar item_id, product_code → Narvar sku
    # MAO's ItemId maps to product_sku but matches Narvar's item_id
    if item_shipment is None:
        for shipment in shipments:
            if item[1] and any(i.get("item_id") == item[1] for i in shipment.get("items_info", [])):
                item_shipment = shipment
                break
        else:
            for shipment in shipments:
                if item[0] and any(i.get("sku") == item[0] for i in shipment.get("items_info", [])):
                    item_shipment = shipment
                    break

    if item_shipment is None:
        return None

    shipment_status_code = item_shipment.get("status_code")
    if shipment_status_code is None:
        return None

    # if shipment_status_code in HANDOFF_STATUS_CODE:
    #   raise Exception(f"Narvar shipment handoff code: {shipment_status_code}")

    delivery_date = item_shipment["delivery"].get("guaranteed_date") or item_shipment[
        "delivery"
    ].get("estimated_date")
    status_location = item_shipment.get("status_location")

    return NarvarShipmentDetail(
        item_shipment["status"], shipment_status_code, status_location, delivery_date
    )


def get_narvar_api(conv):
    """Return MockNarvarClient when USE_MOCK_API is set, otherwise None (use module functions directly)."""
    if getattr(conv.state, "USE_MOCK_API", False):
        from .mock_api import get_mock_narvar

        return get_mock_narvar()
    return None


@func_description("Client for Narvar APIs. It's used to get shipping information.")
def narvar_client(conv: Conversation):
    # Add your function definition here.
    # You can optionally return a string that will be fed back to the LLM.
    x = get_shipping_status_detail(conv, "U7308289609060847616-90BKXBU5OE", ("9356255", "ARA41800"))
    return x.__dict__
    return track_by_order_number(conv, "V4019320300-LNGWBNNB1ZM")
