import json
from http import HTTPStatus
from time import time

import plog
import requests
from _gen import *  # <AUTO GENERATED>
from functions.get_token import get_token

BASE_URL = "https://platform.opentable.com/inhouse/v1"
TIMEOUT = 8

POLYAI_BASE_URL = "https://api.uk-1.platform.polyai.app"


def opentable_proxy(conv: Conversation, method: str, endpoint: str, data: str, params: str):
    url = f"{POLYAI_BASE_URL}/v2/opentable/{conv.account_id}/{conv.project_id}/proxy-request"
    if isinstance(data, str):
        payload = json.loads(data)
    else:
        payload = data
    payload["rid"] = conv.variant.rid
    payload["client_token"] = conv.variant.client_token
    payload["method"] = method
    payload["endpoint"] = endpoint
    payload = json.dumps(payload)
    headers = {"Content-Type": "application/json"}

    res = requests.request(
        "POST", url, headers=headers, data=payload, params=params, timeout=TIMEOUT
    )
    plog.info(
        "OpenTable API call",
        params=params,
        json=data,
        endpoint=endpoint,
        url=url,
        result=res.text,
    )
    return res


@func_description("(WIP) Tools for interacting with OpenTable API")
@func_parameter("method", "REST method")
@func_parameter("endpoint", "endpoint")
@func_parameter("data", "dict with data")
@func_parameter("params", "dict with params")
def opentable_api(conv: Conversation, method: str, endpoint: str, data: str, params: str):
    t1 = time()
    token = get_token(conv)
    t2 = time()
    elapsed = t2 - t1
    url = f"{BASE_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    res = requests.request(
        method=method,
        json=data,
        url=url,
        params=params,
        headers=headers,
        timeout=TIMEOUT - elapsed,
    )
    # res = opentable_proxy(conv, method, endpoint, data, params)

    if not res.ok:
        code = None
        if res.status_code in [HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND]:
            error_data = res.json()
            for error in error_data.get("errors", []):
                code = error.get("code")
                if code:
                    conv.write_metric("API_ERROR", code)
        if not code:
            conv.write_metric("API_ERROR", res.text)

    return res


class OpenTableApiWrapper:
    """Wraps the raw ``opentable_api()`` function into the same method interface
    used by ``MockOpenTableApi``, so callers can be backend-agnostic."""

    def __init__(self, conv):
        self.conv = conv

    # -- helpers --

    @property
    def _rid(self):
        return self.conv.variant.rid

    # -- public API --

    def check_availability(
        self,
        party_size,
        date_time,
        forward_minutes=120,
        backward_minutes=0,
        include_experiences=False,
    ):
        params = {
            "party_size": int(party_size),
            "start_date_time": date_time,
            "forward_minutes": forward_minutes,
            "backward_minutes": backward_minutes,
        }
        if include_experiences:
            params["include_experiences"] = True
        return opentable_api(
            self.conv,
            method="GET",
            endpoint=f"availability/{self._rid}",
            data={},
            params=params,
        )

    def lock_booking(
        self,
        party_size,
        date_time,
        table_type="default",
        experience_id=None,
    ):
        data = {
            "restaurant_id": self._rid,
            "party_size": int(party_size),
            "date_time": date_time,
            "table_type": table_type,
            "experience_id": experience_id,
        }
        return opentable_api(
            self.conv,
            method="POST",
            endpoint=f"booking/{self._rid}/locks",
            data=data,
            params={},
        )

    def finalize_booking(
        self,
        first_name,
        last_name,
        phone_number,
        country_code,
        reservation_token,
        special_request="",
        table_type="default",
        experience=None,
    ):
        data = {
            "first_name": first_name,
            "last_name": last_name,
            "phone": {
                "number": str(phone_number),
                "country_code": int(country_code),
            },
            "restaurant_id": self._rid,
            "reservation_token": reservation_token,
            "sms_notifications_opt_in": True,
            "special_request": special_request,
            "table_type": table_type,
            "experience": experience,
        }
        return opentable_api(
            self.conv,
            method="POST",
            endpoint=f"booking/{self._rid}/reservations",
            data=data,
            params={},
        )

    def cancel_booking(self, booking_id):
        return opentable_api(
            self.conv,
            method="DELETE",
            endpoint=f"booking/{self._rid}/reservations/{booking_id}",
            data={},
            params={},
        )

    def modify_booking(
        self,
        booking_id,
        party_size=None,
        date_time=None,
        special_request=None,
    ):
        data = {
            "party_size": party_size,
            "date_time": date_time,
            "special_request": special_request,
        }
        return opentable_api(
            self.conv,
            method="PUT",
            endpoint=f"booking/{self._rid}/reservations/{booking_id}",
            data=data,
            params={},
        )

    def guest_search(self, phone_number):
        """Delegates to the standalone guest_search module."""
        from functions.guest_search import run_guest_search

        run_guest_search(self.conv, phone_number=phone_number)
        return {
            "count": len(self.conv.state.guest_search_candidates or []),
            "candidates": self.conv.state.guest_search_candidates or [],
            "primaryGuest": self.conv.state.guest_search_primary,
        }

    def get_bookings(self, phone_number, country_code="1"):
        data = {
            "phone": {
                "number": str(phone_number).removeprefix("0"),
                "country_code": int(country_code),
            },
        }
        return opentable_api(
            self.conv,
            method="POST",
            endpoint=f"booking/{self._rid}/reservations/search",
            data=data,
            params={},
        )


def get_restaurant_api(conv):
    """Factory: return mock or real API based on runtime config flag."""
    try:
        flags = conv.real_time_config.get("flags") or {}
        use_real = flags.get("use_real_api")
    except Exception:
        use_real = False
    if use_real:
        return OpenTableApiWrapper(conv)
    from functions.mock_api import MockOpenTableApi

    return MockOpenTableApi(conv)
