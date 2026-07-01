import json
import re
import time
from typing import Any, Optional
from urllib.parse import urlencode

import requests
from _gen import *  # <AUTO GENERATED>
from boto3 import client
from requests.auth import AuthBase, HTTPBasicAuth
from utils.secret_vault import secret_vault

# Configure these IDs from your Zendesk instance
CUSTOM_FIELD_IDS = {
    "pre-release": {
        "first_name": 0,
        "last_name": 0,
        "loyalty_number": 0,
        "postal_code": 0,
    },
    "production": {
        "first_name": 0,
        "last_name": 0,
        "loyalty_number": 0,
        "postal_code": 0,
    },
}

BRAND_ID_MAP = {
    "uat": {
        "Poly Store": 0,
    },
    "prod": {
        "Poly Store": 0,
    },
}


def _digits_only(s):
    return re.sub(r"\D+", "", s or "")


def _normalize_phone_for_zendesk(number: str) -> str:
    d = _digits_only(number)
    return d[1:] if len(d) == 11 and d.startswith("1") else d


class ZendeskAuth(AuthBase):
    def __init__(self, conv: Conversation, base_url: str):
        try:
            self.conv = conv
            self.base_url = base_url
            self.secret_client = client("secretsmanager")
            self.get_access_token()
        except Exception as e:
            self.conv.log.error("Error initializing ZendeskAuth", error=str(e))
            raise
        if time.time() > self.ttl - (20 * 60):
            try:
                self.conv.log.info("Refreshing Zendesk token")
                self.refresh_access_token()
                self.conv.log.info("Zendesk token refreshed")
            except Exception as e:
                self.conv.log.error("Error refreshing Zendesk token", error=str(e))
                raise

    def get_access_token(self):
        secret = self.secret_client.get_secret_value(
            SecretId=f"secret-service-us-1-prod/integrations/zendesk/{self.conv.account_id}/{self.conv.project_id}"
        )
        secret = json.loads(secret.get("SecretString"))
        self.access_token = secret["access_token"]
        self.refresh_token = secret["refresh_token"]
        self.ttl = int(secret["ttl"])

    def refresh_access_token(self):
        try:
            url = f"{self.base_url}/oauth/tokens"
            payload = {
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
                "client_id": "zdg-polyai",
                "expires_in": 172800,
            }
            response = requests.post(url, data=payload)
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            self.ttl = time.time() + int(response.json()["expires_in"])
            self.refresh_token = response.json()["refresh_token"]
            refresh_token_ttl = time.time() + int(
                response.json().get("refresh_token_expires_in", 2592000)
            )
        except Exception as e:
            self.conv.log.error("Error refreshing Zendesk token", error=str(e))
            raise
        try:
            self.secret_client.put_secret_value(
                SecretId=f"secret-service-us-1-prod/integrations/zendesk/{self.conv.account_id}/{self.conv.project_id}",
                SecretString=json.dumps(
                    {
                        "access_token": self.access_token,
                        "refresh_token": self.refresh_token,
                        "ttl": int(self.ttl),
                        "refresh_token_ttl": int(refresh_token_ttl),
                    }
                ),
            )
            self.conv.log.info("Zendesk token updated in secret vault")
        except Exception as e:
            self.conv.log.error("Error updating Zendesk token in secret vault", error=str(e))
            raise e

    def _retry_on_401(self, resp, **kwargs):
        """Retry request on 401 by refreshing token"""
        if resp.status_code == 401 and not getattr(resp.request, "_retried", False):
            self.conv.log.warning("Received 401, refreshing token and retrying")
            resp.close()
            self.get_access_token()
            new_req = resp.request.copy()
            new_req._retried = True
            new_req.headers["Authorization"] = f"Bearer {self.access_token}"
            return resp.connection.send(new_req, **kwargs)
        return resp

    def __call__(self, req):
        req.headers["Authorization"] = f"Bearer {self.access_token}"
        return req


ZENDESK_OAUTH: Optional[ZendeskAuth] = None
USE_OAUTH = False  # Flag to track if we're using OAuth or API key auth


def _load_api_config(conv: Conversation) -> tuple[str, str, str]:
    """Load API config from secret vault.

    Returns:
      Tuple of (api_key, email_address, base_url)
    """
    TESTING_ENV = ["draft", "sandbox", "pre-release"]
    if conv.env in TESTING_ENV:
        conv.log.info("Using test env Zendesk API")
        zendesk_auth_token = secret_vault("zendesk_sandbox_api")
    else:
        zendesk_auth_token = secret_vault("zendesk_prod_api")
    api_key = zendesk_auth_token.get("API_KEY")
    email_address = zendesk_auth_token.get("EMAIL_ADDRESS")
    base_url = zendesk_auth_token.get("BASE_URL")
    return api_key, email_address, base_url


def _safe_parse_json(resp: requests.Response):
    try:
        return resp.json()
    except (ValueError, json.JSONDecodeError):
        return None


def _make_request(
    conv: Conversation,
    http_method: str,
    url: str,
    payload=None,
    params: Optional[dict[str, Any]] = None,
):
    global ZENDESK_OAUTH, USE_OAUTH

    headers = {"Content-Type": "application/json"}

    if USE_OAUTH:
        # OAuth mode - add marketplace headers and use OAuth auth
        headers.update(
            {
                "X-Zendesk-Marketplace-Name": "PolyAI",
                "X-Zendesk-Marketplace-Organization-Id": "3409",
                "X-Zendesk-Marketplace-App-Id": "268939",
            }
        )
        if ZENDESK_OAUTH is None:
            raise RuntimeError("Zendesk OAuth not initialized. Call init_zendesk_client() first.")
        auth = ZENDESK_OAUTH
        hooks = {"response": ZENDESK_OAUTH._retry_on_401}
    else:
        # API key mode - use HTTPBasicAuth
        auth = HTTPBasicAuth(
            f"{conv.state.zendesk_email_address}/token", conv.state.zendesk_api_key
        )
        hooks = None

    if payload is not None:
        conv.log.info(
            "Zendesk request payload", url=url, method=http_method, payload=json.dumps(payload)
        )

    response = requests.request(
        method=http_method,
        url=url,
        auth=auth,
        headers=headers,
        json=payload,
        params=params,
        hooks=hooks,
    )

    preview = (response.text or "")[:500]

    if response.status_code in (200, 201):
        conv.log.info("_make_request ok", url=url, status=response.status_code, preview=preview)
        parsed = _safe_parse_json(response)
        return (
            parsed
            if parsed is not None
            else {"_raw_text": response.text, "_status_code": response.status_code}
        )

    if response.status_code == 204:
        conv.log.info("_make_request no content", url=url, status=response.status_code)
        return {"_raw_text": "", "_status_code": 204}

    if response.status_code == 404:
        conv.log.warning("_make_request 404", url=url, status=response.status_code, preview=preview)
        parsed = _safe_parse_json(response)
        return parsed if parsed is not None else {"_raw_text": response.text, "_status_code": 404}

    conv.log.error(
        "ZENDESK API _make_request error", url=url, status=response.status_code, preview=preview
    )
    response.raise_for_status()
    return _safe_parse_json(response) or {
        "_raw_text": response.text,
        "_status_code": response.status_code,
    }


def search_user(conv: Conversation, email: str):
    mock = get_zendesk_api(conv)
    if mock:
        return mock.search_user(conv, email)
    query = f"role:end-user email:{email}"
    q = urlencode({"query": query})
    url = f"{conv.state.zendesk_base_url}/api/v2/search.json?{q}"
    return _make_request(conv, "GET", url, None)


def search_user_phone(conv: Conversation, phone_number: str):
    mock = get_zendesk_api(conv)
    if mock:
        return mock.search_user_phone(conv, phone_number)
    # Phone search (used in draft/sandbox)
    query = f"role:end-user phone:{phone_number}"
    q = urlencode({"query": query})
    url = f"{conv.state.zendesk_base_url}/api/v2/search.json?{q}"
    return _make_request(conv, "GET", url, None)


def create_ticket(conv: Conversation):
    """Create Zendesk ticket; retry once if the first attempt fails."""
    mock = get_zendesk_api(conv)
    if mock:
        return mock.create_ticket(conv)
    url = f"{conv.state.zendesk_base_url}/api/v2/tickets"
    caller_for_zd = _normalize_phone_for_zendesk(conv.state.phone_number or "").replace("+1", "")
    requester = f"Caller {caller_for_zd}" if conv.state.phone_number else f"Chat user {conv.id}"

    env = "prod" if (conv.env == "live") else "uat"
    brand_id = (
        BRAND_ID_MAP.get(env, {}).get(conv.variant.brand_name) if conv.variant.brand_name else None
    )

    payload = {
        "ticket": {
            "status": "new",
            "subject": f"Conversation with {caller_for_zd}",
            "comment": {
                "body": f"Call ID: {conv.id}\nCaller Number: {caller_for_zd or 'N/A - Assistant Chat'}"
            },
            "via_id": 34,
            "ticket_form_id": 0,  # Configure from your Zendesk instance
        }
    }

    if brand_id:
        payload["ticket"]["brand_id"] = brand_id
    brand_tags = {
        "Poly Store": "polyai_ps",
    }
    tag = brand_tags.get(conv.state.brand)
    if tag:
        payload["ticket"]["tags"] = [tag]
    if requester_id := conv.state.zendesk_user_id:
        payload["ticket"]["requester_id"] = requester_id
    else:
        payload["ticket"]["requester"] = {
            "name": requester,
            "phone": caller_for_zd,
            "shared_phone_number": False,
        }

    attempt = 0
    while attempt < 2:
        try:
            resp = _make_request(conv, "POST", url, payload)

            ticket = None
            ticket_id = None

            if isinstance(resp, dict):
                ticket = resp.get("ticket")
                if ticket and isinstance(ticket, dict):
                    ticket_id = ticket.get("id")
                else:
                    ticket_id = resp.get("id")
            elif hasattr(resp, "get"):
                ticket_id = resp.get("id")

            if ticket_id is not None:
                conv.state.zendesk_ticket_id = ticket_id
                if ticket and isinstance(ticket, dict):
                    rid = ticket.get("requester_id")
                    if rid:
                        conv.state.zendesk_user_id = rid
                        conv.state.zd_requester_id = int(rid)
                conv.write_metric("ZENDESK_TICKET_CREATED")
                conv.write_metric("ZENDESK_TICKET_ID", str(conv.state.zendesk_ticket_id))
                conv.log.info(
                    "Zendesk ticket created successfully",
                    ticket_id=ticket_id,
                    requester_id=conv.state.zendesk_user_id,
                    has_ticket_object=bool(ticket),
                )
                return resp
            else:
                raise ValueError("Zendesk returned no ticket data or ticket ID")
        except Exception as e:
            attempt += 1
            if attempt < 2:
                conv.log.warning(
                    "Retrying Zendesk create_ticket after failure", attempt=attempt, error=str(e)
                )
            else:
                conv.log.error("Zendesk create_ticket failed after retry", error=str(e))
                raise


def get_ticket_field(conv: Conversation, ticket_field_id: str):
    """Get ticket field"""
    url = f"{conv.state.zendesk_base_url}/api/v2/ticket_fields/{ticket_field_id}"
    resp = _make_request(conv, "GET", url, None)
    return resp


def update_ticket(
    conv: Conversation, ticket_id: str, ticket_status: str, comment: dict[str, str], **properties
):
    """Update Zendesk ticket `ticket_id`"""
    mock = get_zendesk_api(conv)
    if mock:
        return mock.update_ticket(conv, ticket_id, ticket_status, comment, **properties)
    url = f"{conv.state.zendesk_base_url}/api/v2/tickets/{ticket_id}"
    payload = {
        "ticket": {"status": ticket_status, "comment": comment, **properties},
    }
    resp = _make_request(conv, "PUT", url, payload)
    print(resp)
    return resp


# def _get_api_creds  TODO: we should not store the api key in state as it's visible in dd so fetch it every time


def init_zendesk_client(conv: Conversation):
    """Init Zendesk Client setting the API config in state and initializing OAuth or API key auth.

    This function needs to be called as first thing in the start_function.

    OAuth is used for pre-release (testing) and live/prod environments.
    API key auth is used for other environments (sandbox, draft).
    """
    mock = get_zendesk_api(conv)
    if mock:
        return mock.init_zendesk_client(conv)

    global ZENDESK_OAUTH, USE_OAUTH

    # Use OAuth for live/prod, API key for others
    USE_OAUTH = conv.env in ("live")

    conv.state.zendesk_api_key, conv.state.zendesk_email_address, conv.state.zendesk_base_url = (
        _load_api_config(conv)
    )

    if USE_OAUTH:
        conv.log.info("Initializing Zendesk OAuth", env=conv.env)
        ZENDESK_OAUTH = ZendeskAuth(conv, conv.state.zendesk_base_url)
    else:
        conv.log.info("Using Zendesk API key authentication", env=conv.env)
        ZENDESK_OAUTH = None


@func_description(
    "Client for Zendesk APIs. It's used to manage Zendesk tickets and other Zendesk related operations."
)
def zendesk_client(conv: Conversation):
    """Define Zendesk client module"""
    pass


def get_zendesk_api(conv):
    """Return MockZendeskClient when USE_MOCK_API is set, otherwise None (use module functions directly)."""
    if getattr(conv.state, "USE_MOCK_API", False):
        from .mock_api import get_mock_zendesk

        return get_mock_zendesk()
    return None


def update_custom_fields_on_ticket(
    conv: Conversation,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    loyalty_number: Optional[str] = None,
    postal_code: Optional[str] = None,
):
    """Update only the custom fields on a Zendesk ticket."""
    mock = get_zendesk_api(conv)
    if mock:
        return mock.update_custom_fields_on_ticket(
            conv, first_name, last_name, loyalty_number, postal_code
        )
    ticket_id = conv.state.zendesk_ticket_id
    if not ticket_id:
        raise ValueError("Ticket ID not set in conv.state.zendesk_ticket_id")

    env_key = "pre-release" if conv.state.Env == "pre-release" else "production"
    field_ids = CUSTOM_FIELD_IDS[env_key]

    fields_to_update = []
    if first_name:
        fields_to_update.append({"id": field_ids["first_name"], "value": first_name})
    if last_name:
        fields_to_update.append({"id": field_ids["last_name"], "value": last_name})
    if loyalty_number:
        fields_to_update.append({"id": field_ids["loyalty_number"], "value": loyalty_number})
    if postal_code:
        fields_to_update.append({"id": field_ids["postal_code"], "value": postal_code})

    if not fields_to_update:
        conv.log.info("No custom fields provided to update.")
        return None

    payload = {"ticket": {"custom_fields": fields_to_update}}

    url = f"{conv.state.zendesk_base_url}/api/v2/tickets/{ticket_id}"
    resp = _make_request(conv, "PUT", url, payload)
    conv.state.ticket_details_updated = True
    return resp
