from dataclasses import dataclass

from _gen import *  # <AUTO GENERATED>

# Narvar status code descriptions used by NarvarShipmentDetail.get_line_description()
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
    conv: Conversation, order_number: str, item: tuple[str | None, str | None]
) -> NarvarShipmentDetail | None:
    """Get shipping status for an order line.

    Delegates to the mock/real backend returned by get_narvar_api().
    Replace get_narvar_api() with your shipping provider integration.
    """
    api = get_narvar_api(conv)
    if api:
        return api.get_shipping_status_detail(conv, order_number, item)
    # No real implementation -- add your shipping provider integration here.
    conv.log.warning(
        "narvar_client: no backend configured for get_shipping_status_detail"
    )
    return None


def get_narvar_api(conv):
    """Return MockNarvarClient when USE_MOCK_API is set, otherwise None.

    To integrate a real shipping provider, return your client object here instead of None.
    """
    if getattr(conv.state, "USE_MOCK_API", False):
        from .mock_api import get_mock_narvar

        return get_mock_narvar()
    return None


@func_description("Client for shipping status APIs")
def narvar_client(conv: Conversation):
    pass
