import re
import time
from typing import Any, Optional

import requests
from _gen import *  # <AUTO GENERATED>
from utils.secret_vault import secret_vault

Json = dict[str, Any]

UAT_ENVS = {"sandbox", "pre-release"}
PROD_ENVS = {"draft", "live"}


def _extract_email_from_payload(payload: Any) -> Optional[str]:
    """
    Returns the first email found in the payload.
    Handles shapes:
      - [ { "email": ... }, ... ]
      - { "email": ... }
      - { "results" | "data" | "customers" | "items": [ { "email": ... }, ... ] }
    """
    if payload is None:
        return None

    # list of customers
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                email = item.get("email")
                if isinstance(email, str) and email:
                    return email
        return None

    # dict payload
    if isinstance(payload, dict):
        # direct email
        email = payload.get("email")
        if isinstance(email, str) and email:
            return email

        # wrapped list patterns
        for key in ("results", "data", "customers", "items"):
            lst = payload.get(key)
            if isinstance(lst, list):
                for item in lst:
                    if isinstance(item, dict):
                        email = item.get("email")
                        if isinstance(email, str) and email:
                            return email
        return None

    return None


def get_email_by_phone(
    conv,
    phone_number: str,
    *,
    country_code: Optional[str] = None,
    timeout: Optional[int] = None,
) -> Optional[str]:
    """
    Calls get_customers_by_phone() and returns the first email found (or None).
    """
    mock = get_customer_api(conv)
    if mock:
        return mock.get_email_by_phone(conv, phone_number, timeout=timeout)

    resp = get_customers_by_phone(conv, phone_number, country_code=country_code, timeout=timeout)
    email = _extract_email_from_payload(resp)
    # Optional: light logging without PII
    conv.log.info(
        "CUSTOMER_CORE:get_email_by_phone",
        found=bool(email),
        response_type=type(resp).__name__,
    )
    return email


def _normalize_us_phone(tn: str) -> str:
    """
    Keep digits only. If it looks like US E.164 (11 digits starting with '1'),
    strip the leading 1 and return 10 digits.
    """
    digits = re.sub(r"\D", "", tn or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def _make_jwt(issuer: str, secret: str, ttl: int = 24 * 60 * 60) -> str:
    import jwt

    now = int(time.time())
    payload = {"iss": issuer, "iat": now, "nbf": now - 30, "exp": now + ttl}
    return jwt.encode(payload, secret, algorithm="HS256")


def _select_customer_core_vault(conv) -> str:
    """Pick the secret vault name based on environment."""
    env = (conv.env or "").lower()
    if env in PROD_ENVS:
        return "customer_core_prod_api"
    return "customer_core_uat_api"


def _make_request(
    conv,
    endpoint: str,
    *,
    method: str = "GET",
    params: Optional[dict[str, str]] = None,
    json: Optional[dict[str, Any]] = None,
    timeout: Optional[int] = None,
    extra_headers: Optional[dict[str, str]] = None,
) -> Any:
    """
    Makes a request to <BASE_URL>/<endpoint> with:
      - Authorization: <raw JWT> (no 'Bearer ')
      - X-API-KEY: <api key>
      - JSON body if provided (POST)
    Vault must provide: BASE_URL, API_KEY, CLIENT_SECRET, ISSUER

    Returns:
      - Parsed JSON on 200
      - None on 404 (treated as "no results")
      - Raises for other non-2xx statuses
    """
    vault_name = _select_customer_core_vault(conv)
    creds = secret_vault(vault_name)

    base_url = creds["BASE_URL"].rstrip("/")
    api_key = creds["API_KEY"]
    client_secret = creds["CLIENT_SECRET"]
    issuer = creds.get("ISSUER")

    token = _make_jwt(issuer, client_secret)

    headers = {
        "X-API-KEY": api_key,
        "Authorization": token,
        "Accept": "application/json",
    }
    # Only set Content-Type if sending JSON
    if json is not None:
        headers["Content-Type"] = "application/json"

    if extra_headers:
        headers.update(extra_headers)

    url = f"{base_url}/{endpoint.lstrip('/')}"

    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            params=params,
            json=json,
            timeout=timeout,
        )

        # Try to parse JSON; fall back to text
        try:
            data = resp.json()
        except ValueError:
            data = resp.text

        if resp.status_code == 200:
            conv.log.info(
                "customer_core_api:request_ok",
                status=resp.status_code,
                method=method.upper(),
                url=url,
                params=params,
                json=json,
            )
            return data

        if resp.status_code == 404:
            # Treat as "not found" rather than error
            conv.log.info(
                "customer_core_api:not_found",
                status=resp.status_code,
                method=method.upper(),
                url=url,
                params=params,
                json=json,
            )
            return None

        # Log other non-2xx
        conv.log.error(
            "customer_core_api:request_error",
            status=resp.status_code,
            method=method.upper(),
            url=url,
            params=params,
            json=json,
            response=data,
        )
        resp.raise_for_status()
        return data
    except Exception as e:
        conv.log.exception(
            "customer_core_api:exception",
            error=str(e),
            method=method.upper(),
            url=url,
            params=params,
            json=json,
        )
        raise


def get_customers_by_phone(
    conv,
    phone_number: str,
    *,
    country_code: Optional[str] = None,
    timeout: Optional[int] = None,
) -> Any:
    """
    Calls (POST):
      {BASE_URL}/customers/search
    Body JSON:
      {"mobileNumber": "<10-digit US>"}  [and optionally "countryCode": "1"]

    Returns:
      - Parsed JSON on 200
      - None on 404 (no results)
      - Raises on other errors
    """
    mobile = _normalize_us_phone(phone_number)

    body: dict[str, Any] = {"mobileNumber": mobile}
    if country_code:
        body["countryCode"] = str(country_code)

    # NOTE: The API expects POST + JSON for phone search
    return _make_request(
        conv,
        "customers/search",
        method="POST",
        json=body,
        timeout=timeout,
    )


def get_customer_api(conv):
    """Return MockCustomerCoreApi when USE_MOCK_API is set, otherwise None (use module functions directly)."""
    if getattr(conv.state, "USE_MOCK_API", False):
        from .mock_api import get_mock_customer

        return get_mock_customer()
    return None


@func_description("calls customer_core api")
def customer_core_api(conv: Conversation):
    # Add your function definition here.
    # You can optionally return a string that will be fed back to the LLM.
    pass
