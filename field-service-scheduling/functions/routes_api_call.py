import requests
from _gen import *  # <AUTO GENERATED>

# note that all the endpoints are GET, so this is intentional


def create_appointment(
    conv: Conversation, spot_id: str, start: str, end: str
) -> bool:  # return success
    if getattr(conv.state, "USE_MOCK_API", False):
        conv.log.info("Mock: appointment created", spot_id=spot_id, start=start, end=end)
        return True
    if conv.real_time_config.get("settings", {}).get("mock_appointment_create_and_update"):
        return True

    subscription = conv.state.subscription
    if subscription is None:
        raise ValueError("subscription must be set before calling this function")
    customer_details = conv.state.customer_details
    if customer_details is None:
        raise ValueError("customer_details must be set before calling this function")

    customer_id = customer_details["customerID"]
    if conv.state.due_for_regular_service:
        service_id = subscription["serviceID"]
        subscription_id = subscription["subscriptionID"]
    else:  # set up warranty reservice
        service_id = conv.state.service_type_id_for_warranty_reservice
        subscription_id = "-1"  # ID for stand-alone service (apparently)
    target_services = conv.state.target_service_ids
    do_interior = conv.state.interior_needed
    duration = (
        "40" if do_interior == 2 else "20"
    )  # ie "IF Interior Needed make duration 40 minutes."
    notes = f"30 min text ahead. The user has indicated that the service types ({conv.state.service_names}) are located at: {conv.state.service_location or 'N/A'}."
    if additional_notes := conv.state.additional_notes:
        notes += f" Additional notes: {additional_notes}."
    notes += " Created by PolyAI agent."

    time_window_params = ""
    if start and end:
        time_window_params = f"&start={start}&end={end}"

    response = routes_api_call(
        conv,
        method="GET",
        endpoint="/appointment/create",
        params=f"&customerID={customer_id}&type={service_id}&subscriptionID={subscription_id}&serviceTypes={target_services}&doInterior={do_interior}&duration={duration}&notes={notes}&spotID={spot_id}{time_window_params}",
    )

    if appointment_id := response.get("result"):
        flag_id_for_30_min_text_ahead = ""
        try:
            # each location has a different flag ID for "30 MIN TEXT AHEAD"
            # (or similar, as they may be called slightly different names at each location)
            # this is how you can fetch the flag IDs in the API
            # generic_flags = routes_api_call(
            #   conv,
            #   method="GET",
            #   endpoint="/genericFlag/search",
            #   params=f"&includeData=1&status=1&type=APPT&code=30 MIN TEXT AHEAD",
            # ).get("genericFlags")

            flag_id_for_30_min_text_ahead = {
                "732": "4352",
                "734": "4414",
                "750": "8253",
                "746": "11391",
                "219": "354",
                "741": "6965",
                "726": "1772",  # called "*30 Minute Text Ahead" at Chicago branch
                "719": "12233",
                "751": "8252",
                "603": "6640",  # called "*30 Minute Text Ahead" at Columbus branch
                "736": "5231",
                "11": "890",
                "10": "368",
                "745": "8257",
                "748": "8255",
                "737": "7105",  # called "*30 Minute Text Ahead" at Indianapolis branch
                "15": "871",  # called "*30 Minute Text Ahead" at Kansas City branch
                "604": "1142",
                "749": "8254",
                "753": "8250",
                "725": "1709",  # called "*30 Minute Text Ahead" at Minneapolis branch
                "757": "11483",
                "747": "8256",
                "754": "8249",
                "712": "892",
                "756": "",  # Seattle doesn't have a flag for this
                "733": "4383",
                "718": "11110",
                "606": "521",
                "755": "8248",
                "602": "1140",
                "738": "6168",
            }[customer_details["officeID"]]
        except Exception:
            conv.log.error("location does not have 30 MIN TEXT AHEAD flag", exc_info=True)
            # no need to raise because note is left in notes

        # make separate call to add "30 MIN TEXT AHEAD" flag to appointment
        # because cannot be done in the same call as the appointment creation
        if flag_id_for_30_min_text_ahead:
            routes_api_call(
                conv,
                method="GET",
                endpoint="/genericFlagAssignment/create",
                params=f"&genericFlagID={flag_id_for_30_min_text_ahead}&entityID={appointment_id}&type=APPT",
            )

        # mark appointment as confirmed https://poly-ai.atlassian.net/browse/UTIL-2540
        create_appointment_reminder_response = routes_api_call(
            conv,
            method="GET",
            endpoint="/appointmentReminder/create",
            params=f"&appointmentID={appointment_id}&status=6&text=%22%22&dateSent=%22%22&emailSent=%22%22",  # text, dateSent, and emailSent parameters have to be included but can be empty strings
        )

        if not create_appointment_reminder_response.get("result"):
            conv.log.error("appointment not confirmed", appointment_id=appointment_id)
            # no need to raise

        return True
    return False


def get_service_type_id_for_warranty_reservice(conv: Conversation):
    try:
        # each location has a different service ID for "Warranty Reservice", so fetch it
        service_types = routes_api_call(
            conv,
            method="GET",
            endpoint="/serviceType/search",
            params="&description=Warranty Reservice&includeData=1",
        ).get("serviceTypes")
        service_types = [
            service_type for service_type in service_types if service_type.get("visible", 0) == "1"
        ]

        if not service_types:  # it may be called "- Warranty Reservice" in some branches
            service_types = routes_api_call(
                conv,
                method="GET",
                endpoint="/serviceType/search",
                params="&description=- Warranty Reservice&includeData=1",
            ).get("serviceTypes")
            service_types = [
                service_type
                for service_type in service_types
                if service_type.get("visible", 0) == "1"
            ]

        if service_types:
            return service_types[0].get("typeID")
    except Exception:
        conv.log.error("location does not have Warranty Reservice service type", exc_info=True)
        raise


def update_appointment(
    conv: Conversation,
    appointment_id: str,
    route_id: str,
    current_appointment_date: str,
    spot_id: str,
    start: str,
    end: str,
):
    if getattr(conv.state, "USE_MOCK_API", False):
        conv.log.info("Mock: appointment updated", appointment_id=appointment_id)
        return appointment_id
    if conv.real_time_config.get("settings", {}).get("mock_appointment_create_and_update"):
        return appointment_id

    time_window_params = ""
    if start and end:
        time_window_params = f"&start={start}&end={end}"

    response = routes_api_call(
        conv,
        method="GET",
        endpoint="/appointment/update",
        params=f"&appointmentID={appointment_id}&spotID={spot_id}{time_window_params}",
    )

    # make API call to custom webhook to update technicians on current-day reschedules https://poly-ai.atlassian.net/browse/UTIL-2669
    if current_appointment_date == conv.state.current_date_ymd:
        conv.write_metric("CURRENT_DAY_RESCHEDULE")
        if routes := get_routes(conv, [int(route_id)]):
            route = routes[0]
            if employee_id := route.get("assignedTech"):
                if technicians := routes_api_call(
                    conv,
                    method="GET",
                    endpoint="/employee/get",
                    params=f"&employeeIDs={employee_id}",
                ).get("employees"):
                    technician = technicians[0]
                    if technician:
                        customer_details = conv.state.customer_details
                        if customer_details is None:
                            raise ValueError(
                                "customer_details must be set before calling this function"
                            )
                        current_day_reschedule_webhook_api_call(
                            conv,
                            request_body={
                                "appointmentID": appointment_id,
                                "type": "Reschedule",
                                "branchID": customer_details["officeID"],
                                "techName": f"{technician['fname']} {technician['lname']}",
                                "techPhone": technician["phone"],
                                "techEmail": technician["email"],
                                "serviceDate": current_appointment_date,
                                "customerID": customer_details["customerID"],
                                "customerFname": customer_details["fname"],
                                "customerLname": customer_details["lname"],
                            },
                        )

    return response.get("result")  # appointment ID which will be the same


def cancel_appointment(conv: Conversation, appointment_id: str, cancel_reason: str):
    if getattr(conv.state, "USE_MOCK_API", False):
        conv.log.info(
            "Mock: appointment cancelled", appointment_id=appointment_id, reason=cancel_reason
        )
        return True
    if conv.real_time_config.get("settings", {}).get("mock_appointment_create_and_update"):
        return True

    response = routes_api_call(
        conv,
        method="GET",
        endpoint="/appointment/cancel",
        params=f"&appointmentID={appointment_id}&cancelReason={cancel_reason}",
    )
    return response.get("success")  # boolean


def get_subscriptions(conv: Conversation):
    customer_details = conv.state.customer_details
    if customer_details is None:
        raise ValueError("customer_details must be set before calling this function")
    subscription_ids = customer_details["subscriptionIDs"]

    response = routes_api_call(
        conv,
        method="GET",
        endpoint="/subscription/get",
        params=f"&subscriptionIDs=[{subscription_ids}]",
    )
    return response.get("subscriptions")


def get_spots_and_routes_and_appointments_in_date_range(
    conv: Conversation, start_date: str, end_date: str
):
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

    route_ids = search_routes(conv, start_date, end_date)
    spot_ids = search_spots(conv, route_ids)
    return (
        get_spots(conv, spot_ids),
        get_routes(conv, route_ids),
        get_appointments_by_routes(conv, route_ids),
    )


def chunks(lst: list, n: int):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def get_spots(conv: Conversation, spot_ids: list):
    customer_details = conv.state.customer_details
    if customer_details is None:
        raise ValueError("customer_details must be set before calling this function")
    latitude = float(customer_details["lat"])
    longitude = float(customer_details["lng"])

    # chunk spots into max 500-long lists to prevent "414 Request-URI Too Long" errors
    chunked_spots = list(chunks(spot_ids, 500))
    conv.log.info(
        f"spot list length is {len(spot_ids)}, chunking into {len(chunked_spots)} api calls",
        len_spot_ids=len(spot_ids),
        len_chunked_spots=len(chunked_spots),
    )

    spots = []
    for spot_ids_to_get in chunked_spots:
        response = routes_api_call(
            conv,
            method="GET",
            endpoint="/spot/get",
            params=f"&spotIDs={spot_ids_to_get}&latitude={latitude}&longitude={longitude}",
        )
        spots.extend(response.get("spots"))
    conv.log.info("received spots", spots=str(spots))
    return spots


def search_spots(conv: Conversation, route_ids: list):
    response = routes_api_call(
        conv,
        method="GET",
        endpoint="/spot/search",
        params=f"&routeIDs={route_ids}",
    )
    return response.get("spotIDs")


def get_routes(conv: Conversation, route_ids: list):
    customer_details = conv.state.customer_details
    if customer_details is None:
        raise ValueError("customer_details must be set before calling this function")
    latitude = float(customer_details["lat"])
    longitude = float(customer_details["lng"])

    response = routes_api_call(
        conv,
        method="GET",
        endpoint="/route/get",
        params=f"&routeIDs={route_ids}&latitude={latitude}&longitude={longitude}",
    )
    return response.get("routes")


def search_routes(conv: Conversation, start_date: str, end_date: str):
    if conv.real_time_config.get("settings", {}).get("use_api_can_schedule_parameter"):
        api_can_schedule_param = "&apiCanSchedule=1"
    else:
        api_can_schedule_param = ""

    response = routes_api_call(
        conv,
        method="GET",
        endpoint="/route/search",
        params=f"&dateStart={start_date}&dateEnd={end_date}&includeData=1{api_can_schedule_param}",
    )

    # manually filter for group title because they can be inconsistently named.
    # groups with these titles are nominally for "Regular Routes", for standard field service
    # Filter for standard route groups (e.g. "Regular Routes", "Quarterly", "Default")
    route_ids = [
        int(route["routeID"])
        for route in response.get("routes")
        if (
            (
                "regular" in route["groupTitle"].lower()
                or "quarterly" in route["groupTitle"].lower()
                or "default" in route["groupTitle"].lower()
            )
            if not conv.real_time_config.get("settings", {}).get("use_dev_api")
            else True
        )
    ]
    return route_ids


def get_service_types(conv: Conversation):
    if getattr(conv.state, "USE_MOCK_API", False):
        from functions.mock_api import SERVICE_TYPES

        return SERVICE_TYPES

    service_type_ids = conv.state.service_type_ids

    response = routes_api_call(
        conv,
        method="GET",
        endpoint="/serviceType/get",
        params=f"&typeIDs={service_type_ids}",
    )
    return response.get("serviceTypes")


def get_office(conv: Conversation):
    response = routes_api_call(
        conv,
        method="GET",
        endpoint="/office/get",
        params="",  # param already passed in
    )
    return response.get("offices")[0]


def search_appointments_by_customer(conv: Conversation):
    if getattr(conv.state, "USE_MOCK_API", False):
        from functions.mock_api import MockDispatchApi

        cid = getattr(conv.state, "customer_id", None) or (
            conv.state.customer_details["customerID"] if conv.state.customer_details else None
        )
        if cid:
            return MockDispatchApi.get_appointments(cid)
        return []

    customer_details = conv.state.customer_details
    if customer_details is None:
        raise ValueError("customer_details must be set before calling this function")
    subscription = conv.state.subscription
    if subscription is None:
        raise ValueError("subscription must be set before calling this function")
    customer_id = customer_details["customerID"]
    service_ids = (
        f"""[{subscription["serviceID"]},{conv.state.service_type_id_for_warranty_reservice}]"""
    )

    response = routes_api_call(
        conv,
        method="GET",
        endpoint="/appointment/search",
        params=f"&customerIDs={customer_id}&serviceIDs={service_ids}&includeData=1",
    )

    return response.get("appointments")


def get_appointments_by_routes(conv: Conversation, route_ids: list):
    response = routes_api_call(
        conv,
        method="GET",
        endpoint="/appointment/search",
        params=f"&routeIDs={route_ids}",
    )

    appointment_ids = response.get("appointmentIDs")

    # chunk appointments into max 500-long lists to prevent "414 Request-URI Too Long" errors
    chunked_appointments = list(chunks(appointment_ids, 500))
    conv.log.info(
        f"appointment list length is {len(appointment_ids)}, chunking into {len(chunked_appointments)} api calls",
        len_appointment_ids=len(appointment_ids),
        len_chunked_appointments=len(chunked_appointments),
    )

    appointments = []
    for appointments_ids_to_get in chunked_appointments:
        response = routes_api_call(
            conv,
            method="GET",
            endpoint="/appointment/get",
            params=f"&appointmentIDs={appointments_ids_to_get}",
        )
        appointments.extend(response.get("appointments"))
    conv.log.info("received appointments", appointments=str(appointments))
    return appointments


def search_services(conv: Conversation):
    response = routes_api_call(
        conv,
        method="GET",
        endpoint="/service/search",
        params="&visible=1&includeData=1",
    )

    return response.get("services")


# returns a list of customers associated with phone number
def get_customer_details(conv: Conversation):
    if getattr(conv.state, "USE_MOCK_API", False):
        from functions.mock_api import MockDispatchApi

        caller = conv.state.phone_number
        customer = MockDispatchApi.lookup_customer_by_phone(caller or "")
        return [customer] if customer else None

    caller_number = conv.state.phone_number

    response = routes_api_call(
        conv, method="GET", endpoint="/customer/search", params=f"&phone={caller_number}"
    )
    if customer_ids := response.get("customerIDs"):
        response = routes_api_call(
            conv,
            method="GET",
            endpoint="/customer/get",
            params=f"&customerIDs={customer_ids}",
        )
        return response["customers"]
    else:
        return None


class DispatchApiError(Exception):
    """Custom exception for dispatch API errors."""

    pass


TIMEOUT = 10


def current_day_reschedule_webhook_api_call(conv: Conversation, request_body: dict):
    url = "https://hooks.example-services.com/webhook/reschedule"

    conv.state.api_error = False

    try:
        conv.log.info(f"Calling POST {url} API", url=url, request_body=request_body)
        conv.log.info("CALLING API ENDPOINT", url=url)
        response = requests.request(
            method="POST",
            url=url,
            timeout=TIMEOUT,
            json=request_body,
        )
        response.raise_for_status()
        conv.log.info(f"API response from {url}", url=url, response=response.text)
        conv.log.info("API CALL SUCCESSFUL", status=response.status_code, url=url)
        return response.text
    except requests.exceptions.Timeout as e:
        conv.log.error(f"API TIMEOUT for {url}", url=url, exc_info=True)
        conv.state.api_timeout = True
        raise Exception(f"API call due to Timeout: {e}") from e
    except requests.HTTPError as e:
        conv.log.error(f"API HTTP ERROR for {url}", url=url, exc_info=True)
        conv.state.api_error = True
        raise Exception(f"API call failed with status {response.status_code}: {e}") from e
    except Exception as e:
        conv.log.error(f"API OTHER ERROR for {url}", url=url, exc_info=True)
        conv.state.api_error = True
        raise Exception(f"Unexpected error: {e}") from e


@func_description("functions to make api calls")
@func_parameter("method", "The http request method to use")
@func_parameter("endpoint", "The endpoint path")
@func_parameter("params", "input params")
def routes_api_call(conv: Conversation, method: str, endpoint: str, params: str):
    if getattr(conv.state, "USE_MOCK_API", False):
        from functions.mock_api import SERVICE_TYPES, MockDispatchApi

        conv.log.info("Mock API mode", endpoint=endpoint)
        if "/customer/search" in endpoint:
            customer = MockDispatchApi.lookup_customer_by_phone(conv.state.phone_number or "")
            if customer:
                return {"customerIDs": customer["customerID"]}
            return {"customerIDs": None}
        if "/customer/get" in endpoint:
            cid = getattr(conv.state, "customer_id", None)
            if cid:
                customer = MockDispatchApi.lookup_customer_by_phone(conv.state.phone_number or "")
                return {"customers": [customer] if customer else []}
            return {"customers": []}
        if "/appointment/search" in endpoint:
            cid = conv.state.customer_details["customerID"] if conv.state.customer_details else None
            return {"appointments": MockDispatchApi.get_appointments(cid) if cid else []}
        if "/appointment/create" in endpoint:
            return {"success": True, "result": "MOCK-APT-NEW"}
        if "/appointment/update" in endpoint:
            return {"success": True, "result": "MOCK-UPDATED"}
        if "/appointment/cancel" in endpoint:
            return {"success": True}
        if "/serviceType" in endpoint:
            return {"serviceTypes": SERVICE_TYPES}
        if "/subscription" in endpoint:
            return {
                "subscriptions": [
                    {
                        "subscriptionID": "SUB-001",
                        "serviceID": "ST-001",
                        "serviceType": "General Service",
                        "active": "1",
                    }
                ]
            }
        if "/office" in endpoint:
            return {"offices": [{"officeName": "Main Office"}]}
        if "/route" in endpoint or "/spot" in endpoint:
            slots = MockDispatchApi.get_available_slots()
            return {"spots": slots, "routes": [{"routeID": "MOCK-R001"}]}
        return {"success": True, "result": "MOCK-RESULT"}

    if conv.real_time_config.get("settings", {}).get("use_dev_api"):
        conv.log.info("calling dev api")
        creds = conv.utils.get_secret("DISPATCH_API_DEV_CREDENTIALS")
        if isinstance(creds, str):
            raise Exception("creds are type str")
        API_KEY = creds["KEY"]
        API_TOKEN = creds["TOKEN"]
    else:
        conv.log.info("calling prod api")
        creds = conv.utils.get_secret("DISPATCH_API_PROD_CREDENTIALS")
        if isinstance(creds, str):
            raise Exception("creds are type str")
        API_KEY = creds["API_KEY"]
        API_TOKEN = creds["API_TOKEN"]

    if customer_details := conv.state.customer_details:
        office_id = customer_details["officeID"]
    else:
        office_id = 0

    base_url = "https://api.example-dispatch.com"

    auth_params = f"?authenticationToken={API_TOKEN}&authenticationKey={API_KEY}"

    # the /search endpoints use the officeIDs param, while the /update and /create endpoints use officeID
    # it doesn't hurt to pass these as params to all the other endpoints as well, as they are just ignored if not used
    office_id_params = f"&officeIDs={office_id}&officeID={office_id}"

    conv.state.api_error = False

    url = base_url + endpoint + auth_params + office_id_params + params
    try:
        conv.log.info(
            f"Calling {method} {endpoint} API with params {params}",
            method=method,
            endpoint=endpoint,
            params=params,
        )
        conv.log.info("CALLING API ENDPOINT", url=url)
        response = requests.request(method=method, url=url, timeout=TIMEOUT)
        response.raise_for_status()
        conv.log.info(
            f"API response from {endpoint}",
            endpoint=endpoint,
            response=response.json(),
        )
        if not response.json()["success"]:
            conv.log.error(
                "API error message",
                error_message=response.json().get("errorMessage"),
            )
            raise DispatchApiError("API request not successful") from None
        conv.log.info("API CALL SUCCESSFUL", status=response.status_code, url=url)
        return response.json()
    except requests.exceptions.Timeout as e:
        conv.log.error(f"API TIMEOUT for {endpoint}", endpoint=endpoint, exc_info=True)
        conv.state.api_timeout = True
        raise DispatchApiError(f"API call due to Timeout: {e}") from e
    except requests.HTTPError as e:
        conv.write_metric("DISPATCH_API_ERROR", "")
        conv.log.error(f"API HTTP ERROR for {endpoint}", endpoint=endpoint, exc_info=True)
        conv.state.api_error = True
        raise DispatchApiError(f"API call failed with status {response.status_code}: {e}") from e
    except Exception as e:
        conv.log.error(f"API OTHER ERROR for {endpoint}", endpoint=endpoint, exc_info=True)
        conv.state.api_error = True
        raise DispatchApiError(f"Unexpected error: {e}") from e
