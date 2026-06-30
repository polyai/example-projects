import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from urllib.parse import urljoin

import plog
import requests
from _gen import *  # <AUTO GENERATED>
from requests import Response, Session
from requests.auth import AuthBase
from requests.exceptions import JSONDecodeError, RequestException, Timeout


class BaseApiHandler:
    """
    A base API handler that uses composition to wrap a requests Session.
    This centralizes logging, error handling, authentication, etc.
    """

    def __init__(
        self, conv: Conversation, base_url: str, session: Session, store_api_reports: bool = False
    ) -> None:
        """
        :param conv: Agent Studio's Conversation object.
        :param base_url: Base URL for this API (endpoints can be relative).
        :param session: Requests Session object.
        :param store_api_reports: Whether to store API errors and successes in conv.state for batch reporting.
        """
        self.conv = conv
        self.base_url = base_url
        self.session = session
        self.store_api_reports = store_api_reports
        self._api_spans_lock = threading.Lock()

        # Initialize unified storage for API telemetry if storing is enabled
        if store_api_reports:
            with self._api_spans_lock:
                if not hasattr(conv.state, "api_spans") or conv.state.api_spans is None:
                    conv.state.api_spans = []

        return

    def request(
        self,
        method: str,
        endpoint: str,
        timeout: int = 10,
        ignored_status_codes: Optional[list[int]] = None,
        **kwargs,
    ) -> Optional[Response]:
        """
        Execute an HTTP request and return the Response object on success,
        or None if an error/timeout occurs.

        :param method: HTTP method (GET, POST, etc.)
        :param endpoint: Relative path or full URL.
        :param timeout: Max time to wait for a response in seconds.
        :param kwargs: Additional arguments to pass to `requests.Session.request`.
        :return: The requests.Response on success, or None on failure.
        """
        start_ns = time.time_ns()

        url = self._build_full_url(endpoint)
        request_dict = self._build_request_log(method, url, timeout, kwargs)

        self.conv.log.info("Making API request", is_pii=True, request=request_dict)

        try:
            response = self.session.request(method=method, url=url, timeout=timeout, **kwargs)
            self.conv.log_api_response(response)
        except Timeout:
            self._handle_timeout(
                url=url, timeout=timeout, start_ns=start_ns, request_dict=request_dict
            )
            return None
        except Exception as e:
            self._handle_exception(
                url=url, timeout=timeout, start_ns=start_ns, request_dict=request_dict, e=e
            )
            return None

        # Check status code
        # ignored_status_codes suppress metrics and error logs for those specific codes
        ignored_status_codes = set(ignored_status_codes or [])
        if (400 <= response.status_code < 500) and (
            response.status_code not in ignored_status_codes
        ):
            self._handle_client_error(
                response=response,
                url=url,
                timeout=timeout,
                start_ns=start_ns,
                request_dict=request_dict,
            )
        elif response.status_code >= 500 and (response.status_code not in ignored_status_codes):
            self._handle_server_error(
                response=response,
                url=url,
                timeout=timeout,
                start_ns=start_ns,
                request_dict=request_dict,
            )

        end_ns = time.time_ns()

        self._log_completion(response=response, request_dict=request_dict)

        # Store success if request was successful (2xx status code)
        if 200 <= response.status_code < 300:
            self._store_success_event(
                response=response, url=url, timeout=timeout, start_ns=start_ns, end_ns=end_ns
            )

        return response

    def request_many(self, calls: list[dict], max_workers: int = 5) -> list[Optional[Response]]:
        """
        Execute multiple API calls in parallel.
        :param calls: List of dicts matching self.request signature:
                      {"method": "GET", "endpoint": "foo", "timeout": 10, ...}
        :param max_workers: Number of threads to use.
        :return: List of Response or None for each call, in order.
        """
        results: list[Optional[Response]] = [None] * len(calls)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(
                    plog.set_context_in_thread(self.request),
                    call["method"],
                    call["endpoint"],
                    **{k: v for k, v in call.items() if k not in ("method", "endpoint")},
                ): idx
                for idx, call in enumerate(calls)
            }

            for fut in as_completed(future_to_idx):
                idx = future_to_idx[fut]
                try:
                    results[idx] = fut.result()
                except Exception as e:
                    # self.request already logs most failures
                    self.conv.log.error(
                        "Error in concurrent request", is_pii=True, e=str(e), idx=idx
                    )
                    results[idx] = None

        return results

    # -------------------------
    # Helper methods
    # -------------------------

    def _build_full_url(self, endpoint: str) -> str:
        if not endpoint.startswith("http"):
            return urljoin(self.base_url, endpoint)
        return endpoint

    def _build_request_log(self, method: str, url: str, timeout: int, kwargs: dict) -> dict:
        return {
            "method": method,
            "url": url,
            "timeout": timeout,
            "headers": kwargs.get("headers"),
            "params": kwargs.get("params"),
            "data": kwargs.get("data"),
            "json": kwargs.get("json"),
        }

    def _extract_fields_from_json(self, response_json: Optional[dict]) -> dict:
        if not response_json:
            return {
                "success": None,
                "correlation_id": None,
                "api_name": None,
                "version": None,
                "message": None,
            }
        return {
            "success": self.iget(response_json, "success", None),
            "correlation_id": self.iget(response_json, "correlationId"),
            "api_name": self.iget(response_json, "apiName"),
            "version": self.iget(response_json, "version"),
            "message": self.iget(response_json, "message"),
        }

    def _handle_timeout(self, url: str, timeout: int, start_ns: int, request_dict: dict) -> None:
        self.conv.log.error("Request timed out", is_pii=True, request=request_dict)
        self.store_api_event(
            url=url,
            status_code=0,
            timeout=timeout,
            success=False,
            start_ns=start_ns,
            end_ns=time.time_ns(),
            text="TIMEOUT",
        )
        return

    def _handle_exception(
        self, url: str, timeout: int, start_ns: int, request_dict: dict, e: Exception
    ) -> None:
        self.conv.log.error("API request error", is_pii=True, request=request_dict, e=str(e))
        self.store_api_event(
            url=url,
            status_code=1,
            timeout=timeout,
            success=False,
            start_ns=start_ns,
            end_ns=time.time_ns(),
            text=str(e),
        )
        return

    def _handle_client_error(
        self, response: Response, url: str, timeout: int, start_ns: int, request_dict: dict
    ) -> None:
        self.conv.log.error(
            "Unexpected client error API response",
            is_pii=True,
            request=request_dict,
            status=response.status_code,
            text=response.text,
        )
        response_json = self.parse_json_response(response, skip_warning=True)
        fields = self._extract_fields_from_json(response_json)
        self.store_api_event(
            url=url,
            status_code=response.status_code,
            timeout=timeout,
            success=False,
            start_ns=start_ns,
            end_ns=time.time_ns(),
            text=response.text,
            correlation_id=fields["correlation_id"],
            api_name=fields["api_name"],
            version=fields["version"],
            message=fields["message"],
        )
        return

    def _handle_server_error(
        self, response: Response, url: str, timeout: int, start_ns: int, request_dict: dict
    ) -> None:
        self.conv.log.error(
            "Unexpected server error API response",
            is_pii=True,
            request=request_dict,
            status=response.status_code,
            text=response.text,
        )
        response_json = self.parse_json_response(response, skip_warning=True)
        fields = self._extract_fields_from_json(response_json)
        self.store_api_event(
            url=url,
            status_code=response.status_code,
            timeout=timeout,
            success=bool(fields["success"]) if fields["success"] is not None else False,
            start_ns=start_ns,
            end_ns=time.time_ns(),
            text=response.text,
            correlation_id=fields["correlation_id"],
            api_name=fields["api_name"],
            version=fields["version"],
            message=fields["message"],
        )
        return

    def _log_completion(self, response: Response, request_dict: dict) -> None:
        self.conv.log.info(
            "API request completed",
            is_pii=True,
            request=request_dict,
            response={
                "status": response.status_code,
                "raw": response.text,
                "json": self.parse_json_response(response, skip_warning=True),
                "duration": response.elapsed.total_seconds() * 1000,
            },
        )
        return

    def _store_success_event(
        self, response: Response, url: str, timeout: int, start_ns: int, end_ns: int
    ) -> None:
        response_json = self.parse_json_response(response, skip_warning=True)
        if not response_json:
            return
        fields = self._extract_fields_from_json(response_json)
        self.store_api_event(
            url=url,
            status_code=response.status_code,
            timeout=timeout,
            success=True,
            start_ns=start_ns,
            end_ns=end_ns,
            text=None,
            correlation_id=fields["correlation_id"],
            api_name=fields["api_name"],
            version=fields["version"],
            message=None,
        )
        return

    def parse_json_response(
        self, response: Optional[Response], skip_warning=False
    ) -> Optional[dict]:
        """
        Safely parse JSON from a response, returning None if parsing fails or response is None.
        :param response: Response object from requests (or None).
        :return: Parsed JSON dict or None.
        """
        if response is None:
            return None
        try:
            return response.json()
        except JSONDecodeError:
            if not skip_warning:
                self.conv.log.warning(
                    "Failed to parse JSON from response",
                    is_pii=True,
                    status=response.status_code,
                    text_snippet=response.text[:500],
                    text=response.text,
                )
            return None

    def iget(self, obj: Optional[dict], key: str, default=None):
        """
        Case-insensitive dict getter.
        Returns obj[key] in a case-insensitive way when obj is a dict with string keys.
        Falls back to `default` if the key is not present.
        """
        if not isinstance(obj, dict) or not isinstance(key, str) or not key:
            return default
        if key in obj:
            return obj[key]
        lower_key = key.lower()
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() == lower_key:
                return v
        return default

    def iget_in(self, obj: Optional[dict], keys: list[str], default=None):
        """
        Case-insensitive nested dict getter.
        Example: iget_in(d, ["response", "data", "items"]).
        Returns `default` if any step is missing or not a dict.
        """
        current = obj
        for key in keys:
            if not isinstance(current, dict):
                return default
            current = self.iget(current, key)
            if current is None:
                return default
        return current

    def write_api_error_metrics(self, url: str, status_code: int, text: str):
        safe_text = (text or "")[:1000]
        self.conv.write_metric("API_ERROR_URL", url)
        self.conv.write_metric("API_ERROR_STATUS_CODE", status_code)
        self.conv.write_metric("API_ERROR_TEXT", safe_text)
        return

    def store_api_event(
        self,
        url: str,
        status_code: int,
        timeout: int,
        success: bool,
        start_ns: Optional[int] = None,
        end_ns: Optional[int] = None,
        text: Optional[str] = None,
        correlation_id: Optional[str] = None,
        api_name: Optional[str] = None,
        version: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """
        Store an API telemetry event.
        """
        if not self.store_api_reports:
            return
        event = {
            "url": url,
            "status_code": status_code,
            "timeout": timeout,
            "success": success,
            "start_ns": start_ns,
            "end_ns": end_ns,
            "text": text,
            "correlation_id": correlation_id,
            "api_name": api_name,
            "version": version,
            "message": message,
        }
        with self._api_spans_lock:
            if not hasattr(self.conv.state, "api_spans") or self.conv.state.api_spans is None:
                self.conv.state.api_spans = []
            # Write error metrics when this is a failure
            if not success:
                self.write_api_error_metrics(url, status_code, text or "")
            self.conv.state.api_spans.append(event)
        return


class OAuthClientCredentialsAuth(AuthBase):
    """
    A class to handle OAuth client credentials authentication.
    """

    def __init__(
        self, token_url, client_id, client_secret, grant_type="client_credentials", scope=None
    ):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.grant_type = grant_type
        self.scope = scope

        self._session = requests.Session()
        self._lock = threading.Lock()
        self.token = None
        self.token_expires_at = 0

    def get_access_token(self):
        now = time.time()
        # refresh if missing or expired (minus buffer)
        if self.token is None or now >= self.token_expires_at - 60:
            with self._lock:
                if self.token is None or now >= self.token_expires_at - 60:
                    plog.info(
                        "Refreshing OAuth access token"
                    )  # we dont use conv.log here as conv can't be cached in memory
                    payload = {
                        "grant_type": self.grant_type,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    }
                    if self.scope:
                        payload["scope"] = self.scope
                    try:
                        resp = self._session.post(self.token_url, data=payload, timeout=10)
                        resp.raise_for_status()
                        data = resp.json()
                    except (RequestException, ValueError):
                        plog.error(
                            "Error refreshing OAuth access token",
                            token_url=self.token_url,
                            status=resp.status_code,
                            text=resp.text,
                        )
                        raise
                    self.token = data["access_token"]
                    expires = data.get(
                        "expires_in", 3600
                    )  # TODO: update this to the actual expires_in value
                    self.token_expires_at = time.time() + expires
        return self.token

    def __call__(self, req):
        req.headers["Authorization"] = f"Bearer {self.get_access_token()}"
        return req

    def _retry_on_401(self, resp, **kwargs):
        if resp.status_code == 401 and not getattr(resp.request, "_retried", False):
            self.token = None
            self.get_access_token()
            new_req = resp.request.copy()
            new_req._retried = True
            new_req.headers["Authorization"] = f"Bearer {self.token}"
            return resp.connection.send(new_req, **kwargs)
        return resp


@func_description("Base API handler")
def base_api_handler(conv: Conversation):
    pass
