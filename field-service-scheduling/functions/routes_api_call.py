from _gen import *  # <AUTO GENERATED>


class DispatchApiError(Exception):
    """Custom exception for dispatch API errors."""

    pass


def create_appointment(conv: Conversation, spot_id: str, start: str, end: str) -> bool:
    """Create a new appointment. Returns True on success."""
    if getattr(conv.state, "USE_MOCK_API", False):
        conv.log.info(
            "Mock: appointment created", spot_id=spot_id, start=start, end=end
        )
        return True
    # TODO: Implement your dispatch API call here
    raise NotImplementedError(
        "Real API path not implemented — connect your dispatch API"
    )


def update_appointment(
    conv: Conversation,
    appointment_id: str,
    route_id: str,
    current_appointment_date: str,
    spot_id: str,
    start: str,
    end: str,
):
    """Update an existing appointment. Returns the appointment ID."""
    if getattr(conv.state, "USE_MOCK_API", False):
        conv.log.info("Mock: appointment updated", appointment_id=appointment_id)
        return appointment_id
    raise NotImplementedError(
        "Real API path not implemented — connect your dispatch API"
    )


def cancel_appointment(conv: Conversation, appointment_id: str, cancel_reason: str):
    """Cancel an appointment. Returns True on success."""
    if getattr(conv.state, "USE_MOCK_API", False):
        conv.log.info(
            "Mock: appointment cancelled",
            appointment_id=appointment_id,
            reason=cancel_reason,
        )
        return True
    raise NotImplementedError(
        "Real API path not implemented — connect your dispatch API"
    )


def get_spots_and_routes_and_appointments_in_date_range(
    conv: Conversation, start_date: str, end_date: str
):
    """Fetch spots, routes, and appointments for a date range."""
    if getattr(conv.state, "USE_MOCK_API", False):
        from datetime import datetime, timedelta

        from functions.mock_api import MockDispatchApi

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        dates = [(today + timedelta(days=d)).strftime("%Y-%m-%d") for d in range(1, 8)]
        windows = [("09:00:00", "12:00:00"), ("13:00:00", "16:00:00")]
        mock_spots = []
        for i, date in enumerate(dates):
            for j, (start, end) in enumerate(windows):
                mock_spots.append(
                    {
                        "spotID": f"MOCK-SPOT-{i * 2 + j:03d}",
                        "date": date,
                        "start": start,
                        "end": end,
                        "open": "1",
                        "blockReason": "",
                        "routeID": f"MOCK-R{i + 1:03d}",
                        "distanceToPrevious": "0",
                        "spotCapacity": "60",
                        "currentAppointment": "",
                    }
                )
        mock_routes = [
            {"routeID": f"MOCK-R{i + 1:03d}", "date": d, "averageDistance": "0"}
            for i, d in enumerate(dates)
        ]
        cid = getattr(conv.state, "customer_id", None)
        mock_appointments = MockDispatchApi.get_appointments(cid) if cid else []
        return (mock_spots, mock_routes, mock_appointments)

    raise NotImplementedError(
        "Real API path not implemented — connect your dispatch API"
    )


def get_service_types(conv: Conversation):
    """Fetch available service types."""
    if getattr(conv.state, "USE_MOCK_API", False):
        from functions.mock_api import SERVICE_TYPES

        return SERVICE_TYPES
    raise NotImplementedError(
        "Real API path not implemented — connect your dispatch API"
    )


def get_subscriptions(conv: Conversation):
    """Fetch active subscriptions for the current customer."""
    if getattr(conv.state, "USE_MOCK_API", False):
        return [
            {
                "subscriptionID": "SUB-001",
                "serviceID": "ST-001",
                "serviceType": "General Service",
                "active": "1",
            }
        ]
    raise NotImplementedError(
        "Real API path not implemented — connect your dispatch API"
    )


def get_office(conv: Conversation):
    """Fetch office details for the current customer."""
    if getattr(conv.state, "USE_MOCK_API", False):
        return {"officeName": "Main Office"}
    raise NotImplementedError(
        "Real API path not implemented — connect your dispatch API"
    )


def search_services(conv: Conversation):
    """Search for visible services at the current office."""
    if getattr(conv.state, "USE_MOCK_API", False):
        from functions.mock_api import SERVICE_TYPES

        return [
            {"serviceID": st["typeID"], "name": st["description"]}
            for st in SERVICE_TYPES
        ]
    raise NotImplementedError(
        "Real API path not implemented — connect your dispatch API"
    )


def get_service_type_id_for_warranty_reservice(conv: Conversation):
    """Fetch the service type ID used for follow-up / warranty reservice."""
    if getattr(conv.state, "USE_MOCK_API", False):
        return "ST-001"
    raise NotImplementedError(
        "Real API path not implemented — connect your dispatch API"
    )


def search_appointments_by_customer(conv: Conversation):
    """Search for appointments belonging to the current customer."""
    if getattr(conv.state, "USE_MOCK_API", False):
        from functions.mock_api import MockDispatchApi

        cid = getattr(conv.state, "customer_id", None) or (
            conv.state.customer_details["customerID"]
            if conv.state.customer_details
            else None
        )
        if cid:
            return MockDispatchApi.get_appointments(cid)
        return []
    raise NotImplementedError(
        "Real API path not implemented — connect your dispatch API"
    )


def get_customer_details(conv: Conversation):
    """Look up customer details by phone number. Returns a list of matching customers."""
    if getattr(conv.state, "USE_MOCK_API", False):
        from functions.mock_api import MockDispatchApi

        caller = conv.state.phone_number
        customer = MockDispatchApi.lookup_customer_by_phone(caller or "")
        return [customer] if customer else None
    raise NotImplementedError(
        "Real API path not implemented — connect your dispatch API"
    )


@func_description("Dispatch API functions")
def routes_api_call(conv: Conversation):
    pass
