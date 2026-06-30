import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Optional, TypeVar

import plog
import requests
from _gen import *  # <AUTO GENERATED>
from requests import Session
from requests.auth import AuthBase
from requests.exceptions import RequestException

from .base_api_handler import BaseApiHandler
from .mock_api import MockApiHandler
from .nextgen_request_models import (
    AppointmentAvailabilityRequest,
    AppointmentCreateRequest,
    AppointmentPatchRequest,
    AppointmentRescheduleRequest,
    FindPersonRescheduledAppointmentRequest,
    PersonCreateRequest,
    RecallPlanCreateRequest,
    RecallPlanUpdateRequest,
)
from .nextgen_response_models import (
    Appointment,
    AppointmentCategory,
    AppointmentSlot,
    ChartAlert,
    Event,
    ListItem,
    Location,
    Payer,
    Person,
    PersonInsurance,
    Practice,
    Provider,
    RecallPlan,
    Resource,
)

_LOCK = threading.Lock()
_SHARED_SESSIONS_BY_SECRET: dict[str, Session] = {}
_SHARED_CREDS_BY_SECRET: dict[str, dict] = {}
_SESSION_ID_CACHE: dict[tuple, str] = {}
_SESSION_ID_CACHE_LOCK = threading.Lock()
TModel = TypeVar("TModel")


class NextGenApiError(Exception):
    """Raised when NextGen setup or API calls fail in a non-recoverable way."""


class NextGenDuplicatePersonError(NextGenApiError):
    """Raised when create patient hits an existing-person conflict (HTTP 409)."""

    def __init__(self, message: str, response_payload: Optional[Any] = None):
        super().__init__(message)
        self.response_payload = response_payload


class NextGenHttpError(NextGenApiError):
    """Raised when a NextGen endpoint returns a non-success status."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_payload: Optional[Any] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_payload = response_payload


class NextGenOAuthClientCredentialsAuth(AuthBase):
    """
    OAuth2 client_credentials auth for NextGen GSA.
    Includes site_id in token request payload.
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        site_id: str,
        grant_type: str = "client_credentials",
    ):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.site_id = site_id
        self.grant_type = grant_type

        self._session = requests.Session()
        self._lock = threading.Lock()
        self.token: Optional[str] = None
        self.token_expires_at = 0.0

    def get_access_token(self) -> str:
        now = time.time()
        if self.token is None or now >= self.token_expires_at - 60:
            with self._lock:
                if self.token is None or now >= self.token_expires_at - 60:
                    plog.info("Refreshing NextGen OAuth access token")
                    payload = {
                        "grant_type": self.grant_type,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "site_id": self.site_id,
                    }

                    try:
                        resp = self._session.post(self.token_url, data=payload, timeout=10)
                        resp.raise_for_status()
                        data = resp.json()
                    except (RequestException, ValueError):
                        plog.error(
                            "Error refreshing NextGen OAuth access token",
                            token_url=self.token_url,
                            status=getattr(resp, "status_code", None),
                            text=getattr(resp, "text", None),
                        )
                        raise

                    self.token = data["access_token"]
                    expires_in = data.get("expires_in", 3600)
                    self.token_expires_at = time.time() + expires_in
        return self.token

    def __call__(self, req):
        req.headers["Authorization"] = f"Bearer {self.get_access_token()}"
        return req


def _get_first_non_empty(creds: dict, keys: list[str], default: Any = None) -> Any:
    for key in keys:
        value = creds.get(key)
        if value is not None and value != "":
            return value
    return default


def _get_shared_session(conv, api_secret_name: str) -> tuple[Session, dict]:
    global _SHARED_SESSIONS_BY_SECRET, _SHARED_CREDS_BY_SECRET

    with _LOCK:
        if api_secret_name not in _SHARED_SESSIONS_BY_SECRET:
            creds = conv.utils.get_secret(api_secret_name)

            token_url = _get_first_non_empty(
                creds,
                ["token_url", "oauth_token_url"],
            )
            client_id = _get_first_non_empty(creds, ["client_id", "clientId"])
            client_secret = _get_first_non_empty(creds, ["client_secret", "clientSecret"])
            site_id = _get_first_non_empty(creds, ["site_id", "siteId"])

            missing_keys = []
            if not token_url:
                missing_keys.append("token_url")
            if not client_id:
                missing_keys.append("client_id")
            if not client_secret:
                missing_keys.append("client_secret")
            if not site_id:
                missing_keys.append("site_id")

            if missing_keys:
                raise NextGenApiError(
                    f"Missing required NextGen credential fields in secret '{api_secret_name}': {', '.join(missing_keys)}"
                )

            auth = NextGenOAuthClientCredentialsAuth(
                token_url=token_url,
                client_id=client_id,
                client_secret=client_secret,
                site_id=site_id,
            )
            session = Session()
            session.auth = auth

            _SHARED_SESSIONS_BY_SECRET[api_secret_name] = session
            _SHARED_CREDS_BY_SECRET[api_secret_name] = creds

    return _SHARED_SESSIONS_BY_SECRET[api_secret_name], _SHARED_CREDS_BY_SECRET[api_secret_name]


# ---------------------------------------------------------------------------
# Real NextGen API handler (requires live API credentials)
# ---------------------------------------------------------------------------


class NextGenApiHandler(BaseApiHandler):
    """
    Production NextGen EHR API handler. Requires valid API credentials
    configured in Agent Studio secrets. For template/demo use, prefer
    MockApiHandler instead.
    """

    def __init__(
        self,
        conv: Conversation,
        api_secret_name: str,
        enterprise_id: Optional[str] = None,
        practice_id: Optional[str] = None,
    ) -> None:
        shared_session, creds = _get_shared_session(conv, api_secret_name)

        self.creds = creds
        resolved_base_url = _get_first_non_empty(
            creds,
            ["base_url", "api_base_url", "enterprise_api_base_url"],
        )
        if not resolved_base_url:
            raise NextGenApiError(
                f"Missing required NextGen credential field in secret '{api_secret_name}': base_url"
            )
        # Keep internal representation consistent and avoid trailing slash drift.
        self.base_url = str(resolved_base_url).rstrip("/")
        self.enterprise_id = enterprise_id or _get_first_non_empty(
            creds,
            ["enterprise_id", "enterpriseId", "Enterprice ID", "Enterprise ID"],
        )
        self.practice_id = practice_id or _get_first_non_empty(
            creds,
            ["practice_id", "practiceId", "Practice ID"],
        )
        self.static_session_id = _get_first_non_empty(
            creds,
            ["x_ng_sessionid", "x-ng-sessionid", "session_id", "sessionId"],
        )

        _flags = conv.real_time_config.get("flags") or {}
        self.use_mock = bool(_flags.get("use_mock"))

        super().__init__(
            conv=conv,
            base_url=self.base_url,
            session=shared_session,
            store_api_reports=bool(conv.env == "live"),
        )

    # -------------------------
    # Internal helpers
    # -------------------------

    def _normalize_path(self, path: str) -> str:
        return str(path).lstrip("/")

    def _build_endpoint_url(self, path: str) -> str:
        return f"{self.base_url}/{self._normalize_path(path)}"

    def _resolve_endpoint_or_url(self, path_or_url: str) -> str:
        value = str(path_or_url or "")
        if value.startswith("http://") or value.startswith("https://"):
            return value
        if value.startswith("/"):
            return f"{self.base_url}{value}"
        return self._build_endpoint_url(value)

    def _headers_with_session(self) -> Optional[dict]:
        session_id = self.ensure_session_id()
        if not session_id:
            return None
        return {"x-ng-sessionid": session_id}

    def _extract_items(self, payload: Any) -> list[dict]:
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []

        items = self.iget(payload, "items")
        if isinstance(items, list):
            return items
        return []

    def _parse_model_list(self, items: list[dict], model_cls) -> list[TModel]:
        standardized: list[TModel] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            standardized.append(model_cls.model_validate(item))
        return standardized

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json_payload: Optional[dict] = None,
        include_session: bool = True,
        timeout: int = 15,
        ignored_status_codes: Optional[list[int]] = None,
    ) -> Optional[Any]:
        headers = {}
        if include_session:
            session_headers = self._headers_with_session()
            if not session_headers:
                raise NextGenApiError(
                    f"{method} {path} requires x-ng-sessionid, but no session could be established"
                )
            headers.update(session_headers)

        if json_payload is not None:
            headers["Content-Type"] = "application/json"

        response = self.request(
            method=method,
            endpoint=self._resolve_endpoint_or_url(path),
            timeout=timeout,
            ignored_status_codes=ignored_status_codes,
            params=params,
            json=json_payload,
            headers=headers if headers else None,
        )
        if response is None:
            raise NextGenApiError(f"{method} {path} failed without a response")
        if response.status_code >= 400:
            response_payload = self.parse_json_response(response, skip_warning=True)
            raise NextGenHttpError(
                f"{method} {path} failed with status {response.status_code}: {response.text[:500]}",
                status_code=response.status_code,
                response_payload=response_payload,
            )
        return self.parse_json_response(response, skip_warning=True)

    def _request_items_paginated(
        self,
        path: str,
        *,
        params: Optional[dict] = None,
        include_session: bool = True,
        timeout: int = 15,
        ignored_status_codes: Optional[list[int]] = None,
        fetch_all_pages: bool = False,
        max_pages: int = 50,
    ) -> list[dict]:
        if max_pages < 1:
            max_pages = 1

        payload = self._request_json(
            "GET",
            path,
            params=params,
            include_session=include_session,
            timeout=timeout,
            ignored_status_codes=ignored_status_codes,
        )
        items = self._extract_items(payload)
        if not fetch_all_pages:
            return items

        page_count = 1
        next_page_link = None
        if isinstance(payload, dict):
            raw_next_page_link = self.iget(payload, "nextPageLink")
            if isinstance(raw_next_page_link, str) and raw_next_page_link.strip():
                next_page_link = raw_next_page_link.strip()

        visited_links: set[str] = set()
        while next_page_link and page_count < max_pages:
            if next_page_link in visited_links:
                self.conv.log.warning(
                    "Detected cyclic nextPageLink while paginating",
                    link=next_page_link,
                    is_pii=True,
                )
                break
            visited_links.add(next_page_link)

            page_payload = self._request_json(
                "GET",
                next_page_link,
                params=None,
                include_session=include_session,
                timeout=timeout,
                ignored_status_codes=ignored_status_codes,
            )
            items.extend(self._extract_items(page_payload))
            page_count += 1

            next_page_link = None
            if isinstance(page_payload, dict):
                raw_next_page_link = self.iget(page_payload, "nextPageLink")
                if isinstance(raw_next_page_link, str) and raw_next_page_link.strip():
                    next_page_link = raw_next_page_link.strip()

        if next_page_link and page_count >= max_pages:
            self.conv.log.warning(
                "Stopped pagination after reaching max_pages",
                max_pages=max_pages,
                path=path,
                is_pii=True,
            )

        return items

    def _build_filter(self, clauses: list[str]) -> Optional[str]:
        cleaned = [c.strip() for c in clauses if c and c.strip()]
        if not cleaned:
            return None
        return " and ".join(cleaned)

    def _parse_iso_datetime(self, value: Optional[str]) -> Optional[datetime]:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _iso_start_of_day(self, value: datetime) -> str:
        return value.replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

    def _iso_end_of_day(self, value: datetime) -> str:
        return value.replace(hour=23, minute=59, second=59, microsecond=0).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

    def _latest_appointment(self, appointments: list[Appointment]) -> Optional[Appointment]:
        dated = [
            (parsed_date, appointment)
            for appointment in appointments
            if (parsed_date := self._parse_iso_datetime(appointment.appointment_date))
        ]
        if dated:
            return max(dated, key=lambda item: item[0])[1]
        if appointments:
            return appointments[-1]
        return None

    def _session_cache_key(
        self,
        enterprise_id: str,
        practice_id: str,
        location_id: Optional[str] = None,
        provider_id: Optional[str] = None,
        time_zone: Optional[str] = None,
    ) -> tuple:
        return (
            self.base_url,
            str(enterprise_id),
            str(practice_id),
            str(location_id or ""),
            str(provider_id or ""),
            str(time_zone or ""),
        )

    def _extract_header_case_insensitive(self, response, header_name: str) -> Optional[str]:
        if response is None:
            return None
        try:
            for key, value in response.headers.items():
                if key.lower() == header_name.lower():
                    return value
        except Exception:
            return None
        return None

    # -------------------------
    # Session setup
    # -------------------------

    def ensure_session_id(
        self,
        enterprise_id: Optional[str] = None,
        practice_id: Optional[str] = None,
        location_id: Optional[str] = None,
        provider_id: Optional[str] = None,
        time_zone: Optional[str] = None,
    ) -> Optional[str]:
        """
        Resolve x-ng-sessionid for practice-scoped requests using:
          PUT /users/me/login-defaults.
        """
        if self.static_session_id:
            return self.static_session_id

        resolved_enterprise_id = enterprise_id or self.enterprise_id
        resolved_practice_id = practice_id or self.practice_id

        if not resolved_enterprise_id or not resolved_practice_id:
            self.conv.log.error(
                "Missing enterprise/practice IDs required to create x-ng-sessionid",
                enterprise_id=resolved_enterprise_id,
                practice_id=resolved_practice_id,
            )
            return None

        cache_key = self._session_cache_key(
            enterprise_id=resolved_enterprise_id,
            practice_id=resolved_practice_id,
            location_id=location_id,
            provider_id=provider_id,
            time_zone=time_zone,
        )

        with _SESSION_ID_CACHE_LOCK:
            cached = _SESSION_ID_CACHE.get(cache_key)
            if cached:
                return cached

        body = {
            "enterpriseId": str(resolved_enterprise_id),
            "practiceId": str(resolved_practice_id),
        }
        if location_id:
            body["locationId"] = location_id
        if provider_id:
            body["providerId"] = provider_id
        if time_zone:
            body["timeZone"] = time_zone

        response = self.request(
            method="PUT",
            endpoint=self._build_endpoint_url("users/me/login-defaults"),
            timeout=15,
            json=body,
            headers={"Content-Type": "application/json"},
        )
        if response is None or response.status_code >= 400:
            return None

        session_id = self._extract_header_case_insensitive(response, "x-ng-sessionid")
        if not session_id:
            self.conv.log.error(
                "Login defaults call succeeded but x-ng-sessionid was not found in response headers"
            )
            return None

        with _SESSION_ID_CACHE_LOCK:
            _SESSION_ID_CACHE[cache_key] = session_id

        return session_id

    # -------------------------
    # NextGen endpoints for call flows
    # -------------------------

    def get_master_practices(
        self, top: int = 200, fetch_all_pages: bool = False, max_pages: int = 50
    ) -> list[Practice]:
        params = {"$top": top}
        practices = self._request_items_paginated(
            "/master/practices",
            params=params,
            include_session=False,
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(practices, Practice)

    def lookup_patients(
        self,
        phone_number: str,
        date_of_birth: Optional[str] = None,
        expand: str = "chart,insurances",
        search_patients_only: bool = True,
        fetch_all_pages: bool = False,
        max_pages: int = 50,
    ) -> list[Person]:
        params = {
            "quickSearchId": "PhoneNumber",
            "quickSearchInput": phone_number,
            "searchPatientsOnly": str(search_patients_only).lower(),
            "$expand": expand,
        }
        if date_of_birth:
            params["dateOfBirth"] = date_of_birth
        patients = self._request_items_paginated(
            "/persons/lookup",
            params=params,
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(patients, Person)

    def get_person_appointments(
        self,
        person_id: str,
        start_date_iso: Optional[str] = None,
        end_date_iso: Optional[str] = None,
        top: int = 50,
        fetch_all_pages: bool = False,
        max_pages: int = 50,
    ) -> list[Appointment]:
        filters = []
        if start_date_iso:
            filters.append(f"appointmentDate ge dateTime'{start_date_iso}'")
        if end_date_iso:
            filters.append(f"appointmentDate le dateTime'{end_date_iso}'")

        params = {
            "$orderby": "appointmentDate",
            "$top": top,
        }
        filter_clause = self._build_filter(filters)
        if filter_clause:
            params["$filter"] = filter_clause

        path = f"/persons/{person_id}/appointments"
        appointments = self._request_items_paginated(
            path,
            params=params,
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(appointments, Appointment)

    def get_person_insurances(
        self,
        person_id: str,
        fetch_all_pages: bool = False,
        max_pages: int = 50,
    ) -> list[PersonInsurance]:
        path = f"/persons/{person_id}/insurances"
        insurances = self._request_items_paginated(
            path,
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(insurances, PersonInsurance)

    def get_person_chart_alerts(
        self,
        person_id: str,
        fetch_all_pages: bool = False,
        max_pages: int = 50,
    ) -> list[ChartAlert]:
        path = f"/persons/{person_id}/chart/alerts"
        alerts = self._request_items_paginated(
            path,
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(alerts, ChartAlert)

    def find_person_rescheduled_appointment(
        self,
        person_id: str,
        original_appointment_id: str,
        end_date_iso: str,
        start_date_iso: Optional[str] = None,
        top: int = 400,
        fetch_all_pages: bool = True,
        max_pages: int = 50,
    ) -> Optional[Appointment]:
        """
        Find the latest appointment in the date window whose
        rescheduledAppointmentId matches the original appointment id.
        """
        request = FindPersonRescheduledAppointmentRequest.model_validate(
            {
                "PersonId": person_id,
                "RescheduledAppointmentId": original_appointment_id,
                "StartDate": start_date_iso,
                "EndDate": end_date_iso,
                "Top": top,
                "FetchAllPages": fetch_all_pages,
                "MaxPages": max_pages,
            }
        )
        target_end_dt = self._parse_iso_datetime(request.end_date_iso)
        if target_end_dt is None:
            raise NextGenApiError(
                f"Invalid end_date_iso for rescheduled appointment lookup: {request.end_date_iso!r}"
            )
        resolved_end_iso = self._iso_end_of_day(target_end_dt + timedelta(days=1))

        if request.start_date_iso:
            start_dt = self._parse_iso_datetime(request.start_date_iso)
            if start_dt is None:
                raise NextGenApiError(
                    "Invalid start_date_iso for rescheduled appointment lookup: "
                    f"{request.start_date_iso!r}"
                )
        else:
            start_dt = datetime.now(UTC) - timedelta(days=1)
        resolved_start_iso = self._iso_start_of_day(start_dt)

        appointments = self.get_person_appointments(
            request.person_id,
            start_date_iso=resolved_start_iso,
            end_date_iso=resolved_end_iso,
            top=request.top,
            fetch_all_pages=request.fetch_all_pages,
            max_pages=request.max_pages,
        )
        matching = [
            appointment
            for appointment in appointments
            if str(appointment.rescheduled_appointment_id or "") == request.original_appointment_id
        ]
        return self._latest_appointment(matching)

    def get_person_recall_plans(
        self,
        person_id: str,
        *,
        expand: str = "Detail",
        top: int = 50,
        filter_clause: Optional[str] = None,
        orderby: Optional[str] = None,
        skip: Optional[int] = None,
        inlinecount: Optional[str] = None,
        count: Optional[bool] = None,
        fetch_all_pages: bool = False,
        max_pages: int = 50,
    ) -> list[RecallPlan]:
        params: dict[str, Any] = {"$expand": expand, "$top": top}
        if filter_clause:
            params["$filter"] = filter_clause
        if orderby:
            params["$orderby"] = orderby
        if skip is not None:
            params["$skip"] = skip
        if inlinecount:
            params["$inlinecount"] = inlinecount
        if count is not None:
            params["$count"] = str(count).lower()

        path = f"/persons/{person_id}/chart/recall-plans"
        items = self._request_items_paginated(
            path,
            params=params,
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(items, RecallPlan)

    def get_person_recall_plan(
        self,
        person_id: str,
        recall_plan_id: str,
        recall_plan_instance: int,
        *,
        expand: str = "Detail",
    ) -> Optional[dict[str, Any]]:
        params = {"$expand": expand} if expand else None
        path = (
            f"/persons/{person_id}/chart/recall-plans/{recall_plan_id}/{int(recall_plan_instance)}"
        )
        payload = self._request_json("GET", path, params=params)
        if isinstance(payload, dict):
            return payload
        return None

    def create_person_recall_plan(
        self, person_id: str, payload: RecallPlanCreateRequest
    ) -> Optional[dict[str, Any]]:
        request_payload = payload.model_dump(by_alias=True, exclude_none=True)
        response_payload = self._request_json(
            "POST",
            f"/persons/{person_id}/chart/recall-plans",
            json_payload=request_payload,
            timeout=20,
        )
        if isinstance(response_payload, dict):
            return response_payload
        return None

    def update_person_recall_plan(
        self,
        person_id: str,
        recall_plan_id: str,
        recall_plan_instance: int,
        payload: RecallPlanUpdateRequest,
    ) -> Optional[dict[str, Any]]:
        request_payload = payload.model_dump(by_alias=True, exclude_none=True)
        response_payload = self._request_json(
            "PUT",
            (
                f"/persons/{person_id}/chart/recall-plans/"
                f"{recall_plan_id}/{int(recall_plan_instance)}"
            ),
            json_payload=request_payload,
            timeout=20,
        )
        if isinstance(response_payload, dict):
            return response_payload
        return None

    def get_appointment(
        self, appointment_id: str, expand: Optional[str] = None
    ) -> Optional[Appointment]:
        params = {}
        if expand:
            params["$expand"] = expand
        path = f"/appointments/{appointment_id}"
        payload = self._request_json("GET", path, params=params or None)
        if isinstance(payload, dict):
            return Appointment.model_validate(payload)
        return None

    def cancel_appointment(
        self, appointment_id: str, cancel_reason_id: str
    ) -> Optional[Appointment]:
        if self.use_mock:
            plog.info("[MOCK] cancel_appointment: returning mock success (use_mock=True)")
            self.conv.log.info("cancel_appointment: mock mode, skipping real API call")
            return Appointment.model_validate(
                {
                    "appointmentId": appointment_id,
                    "id": appointment_id,
                    "isCancelled": True,
                }
            )

        path = f"/appointments/{appointment_id}/cancel"
        payload = self._request_json(
            "POST",
            path,
            json_payload={"cancelReasonId": cancel_reason_id},
            timeout=20,
        )
        if isinstance(payload, dict):
            return Appointment.model_validate(payload)
        return None

    def confirm_appointment_kept(
        self, appointment_id: str, encounter_id: Optional[str] = None
    ) -> Optional[Appointment]:
        path = f"/appointments/{appointment_id}/kept"
        payload_body: Optional[dict[str, str]] = None
        if encounter_id:
            payload_body = {"encounterId": encounter_id}
        payload = self._request_json("PUT", path, json_payload=payload_body, timeout=20)
        if isinstance(payload, dict):
            return Appointment.model_validate(payload)
        return None

    def patch_appointment(
        self, appointment_id: str, payload: AppointmentPatchRequest
    ) -> Optional[Appointment]:
        if self.use_mock:
            plog.info("[MOCK] patch_appointment: returning mock success (use_mock=True)")
            self.conv.log.info("patch_appointment: mock mode, skipping real API call")
            return Appointment.model_validate(
                {
                    "appointmentId": appointment_id,
                    "id": appointment_id,
                }
            )

        request_payload = payload.model_dump(by_alias=True, exclude_none=True)
        response_payload = self._request_json(
            "PATCH",
            f"/appointments/{appointment_id}",
            json_payload=request_payload,
            timeout=20,
        )
        if isinstance(response_payload, dict):
            return Appointment.model_validate(response_payload)
        return None

    def create_patient(self, payload: PersonCreateRequest) -> Optional[Person]:
        if self.use_mock:
            plog.info("[MOCK] create_patient: returning mock success (use_mock=True)")
            self.conv.log.info("create_patient: mock mode, skipping real API call")
            return Person.model_validate(
                {
                    "id": "mock-person-id",
                    "firstName": payload.first_name,
                    "lastName": payload.last_name,
                }
            )

        request_payload = payload.model_dump(by_alias=True, exclude_none=True)

        headers = self._headers_with_session()
        if not headers:
            raise NextGenApiError("Unable to create patient because x-ng-sessionid is missing")
        headers["Content-Type"] = "application/json"

        response = self.request(
            method="POST",
            endpoint=self._build_endpoint_url("/persons"),
            timeout=20,
            ignored_status_codes=[409],
            json=request_payload,
            headers=headers,
        )
        if response is None:
            raise NextGenApiError("Create patient request failed without a response")

        response_payload = self.parse_json_response(response, skip_warning=True)
        if response.status_code == 409:
            raise NextGenDuplicatePersonError(
                "Create patient returned HTTP 409 (possible duplicate person)",
                response_payload=response_payload,
            )
        if response.status_code >= 400:
            raise NextGenApiError(
                f"Create patient failed with status {response.status_code}: {response.text[:500]}"
            )
        if isinstance(response_payload, dict):
            return Person.model_validate(response_payload)
        return None

    def create_appointment(self, payload: AppointmentCreateRequest) -> Optional[Appointment]:
        if self.use_mock:
            plog.info("[MOCK] create_appointment: returning mock success (use_mock=True)")
            self.conv.log.info("create_appointment: mock mode, skipping real API call")
            return Appointment.model_validate(
                {
                    "appointmentId": "mock-appointment-id",
                    "id": "mock-appointment-id",
                    "personId": payload.person_id,
                    "eventId": payload.event_id,
                    "appointmentDate": payload.appointment_date,
                    "isCancelled": False,
                    "isRescheduled": False,
                }
            )

        request_payload = payload.model_dump(by_alias=True, exclude_none=True)

        headers = self._headers_with_session()
        if not headers:
            raise NextGenApiError("Unable to create appointment because x-ng-sessionid is missing")
        headers["Content-Type"] = "application/json"

        response = self.request(
            method="POST",
            endpoint=self._build_endpoint_url("/appointments"),
            timeout=20,
            json=request_payload,
            headers=headers,
        )
        if response is None:
            raise NextGenApiError("Create appointment request failed without a response")
        if response.status_code >= 400:
            response_payload = self.parse_json_response(response, skip_warning=True)
            raise NextGenHttpError(
                f"POST /appointments failed with status {response.status_code}: {response.text[:500]}",
                status_code=response.status_code,
                response_payload=response_payload,
            )

        # NextGen may return an empty body on success (200/201) -- that is still a success.
        response_payload = self.parse_json_response(response, skip_warning=True)
        if isinstance(response_payload, dict):
            return Appointment.model_validate(response_payload)
        return None

    def reschedule_appointment(
        self, appointment_id: str, payload: AppointmentRescheduleRequest
    ) -> Optional[Appointment]:
        """
        Endpoint based on NextGen docs/PDF flow:
          POST /appointments/{appointmentId}/reschedule
        """
        if self.use_mock:
            plog.info("[MOCK] reschedule_appointment: returning mock success (use_mock=True)")
            self.conv.log.info("reschedule_appointment: mock mode, skipping real API call")
            return None

        request_payload = payload.model_dump(by_alias=True, exclude_none=True)

        headers = self._headers_with_session()
        if not headers:
            raise NextGenApiError(
                "Unable to reschedule appointment because x-ng-sessionid is missing"
            )
        headers["Content-Type"] = "application/json"

        response = self.request(
            method="POST",
            endpoint=self._build_endpoint_url(f"/appointments/{appointment_id}/reschedule"),
            timeout=20,
            json=request_payload,
            headers=headers,
        )
        if response is None:
            raise NextGenApiError("Reschedule appointment request failed without a response")
        if response.status_code >= 400:
            response_payload = self.parse_json_response(response, skip_warning=True)
            raise NextGenHttpError(
                f"POST /appointments/{appointment_id}/reschedule failed with status {response.status_code}: {response.text[:500]}",
                status_code=response.status_code,
                response_payload=response_payload,
            )

        # NextGen may return an empty body on success (200/201/204) -- that is still a success.
        response_payload = self.parse_json_response(response, skip_warning=True)
        if isinstance(response_payload, dict):
            return Appointment.model_validate(response_payload)
        return None

    def search_appointment_slots(
        self,
        start_date_iso: str,
        end_date_iso: Optional[str] = None,
        location_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        category_id: Optional[str] = None,
        only_open_slots: bool = True,
        top: int = 100,
        expand: str = "Resource",
        fetch_all_pages: bool = False,
        max_pages: int = 50,
    ) -> list[AppointmentSlot]:
        filters = [f"startDate ge dateTime'{start_date_iso}'"]
        if end_date_iso:
            filters.append(f"startDate le dateTime'{end_date_iso}'")
        if location_id:
            filters.append(f"locationId eq guid'{location_id}'")
        if resource_id:
            filters.append(f"resourceId eq guid'{resource_id}'")
        if category_id:
            filters.append(f"categoryId eq guid'{category_id}'")
        if only_open_slots:
            filters.append("appointmentCount eq 0")

        params = {
            "$expand": expand,
            "$top": top,
            "$filter": self._build_filter(filters),
            "$orderby": "startDate",
        }

        slots = self._request_items_paginated(
            "/appointments/slots",
            params=params,
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        _log_prefix = "[search_appointment_slots]: "
        plog.info(f"{_log_prefix} api_response={slots}", is_pii=True)
        return self._parse_model_list(slots, AppointmentSlot)

    def search_appointment_availability(
        self, payload: AppointmentAvailabilityRequest
    ) -> list[AppointmentSlot]:
        """Search availability slots via POST /appointments/availability."""
        request_payload = payload.model_dump(by_alias=True, exclude_none=True)
        response_payload = self._request_json(
            "POST",
            "/appointments/availability",
            json_payload=request_payload,
            timeout=20,
        )

        if isinstance(response_payload, list):
            items = [item for item in response_payload if isinstance(item, dict)]
            return self._parse_model_list(items, AppointmentSlot)

        items = self._extract_items(response_payload)
        if not items and isinstance(response_payload, dict):
            for key in ("slots", "availability", "availabilities", "results"):
                candidate = self.iget(response_payload, key)
                if isinstance(candidate, list):
                    items = [item for item in candidate if isinstance(item, dict)]
                    if items:
                        break

        return self._parse_model_list(items, AppointmentSlot)

    def get_providers(
        self,
        practice_id: Optional[str] = None,
        only_rendering_at_practice: bool = True,
        include_deleted: bool = False,
        top: int = 200,
        fetch_all_pages: bool = False,
        max_pages: int = 50,
    ) -> list[Provider]:
        filters = []
        if not include_deleted:
            filters.append("isDeleted eq false")
        if only_rendering_at_practice:
            filters.append("isRenderingAtPractice eq true")
        if practice_id:
            filters.append(f"practiceId eq '{practice_id}'")

        params = {"$top": top}
        filter_clause = self._build_filter(filters)
        if filter_clause:
            params["$filter"] = filter_clause

        providers = self._request_items_paginated(
            "/providers",
            params=params,
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(providers, Provider)

    def get_provider(
        self, provider_id: str, expand: Optional[str] = "Practice"
    ) -> Optional[Provider]:
        params = {}
        if expand:
            params["$expand"] = expand
        payload = self._request_json("GET", f"/providers/{provider_id}", params=params or None)
        if isinstance(payload, dict):
            return Provider.model_validate(payload)
        return None

    def get_person(self, person_id: str) -> Optional[Person]:
        payload = self._request_json("GET", f"/persons/{person_id}")
        if isinstance(payload, dict):
            return Person.model_validate(payload)
        return None

    def get_resource(self, resource_id: str) -> Optional[Resource]:
        payload = self._request_json("GET", f"/resources/{resource_id}")
        if isinstance(payload, dict):
            return Resource.model_validate(payload)
        return None

    def list_resources(
        self,
        resource_type: str = "Person",
        only_active: bool = False,
        expand: str = "Resource",
        top: int = 200,
        fetch_all_pages: bool = True,
        max_pages: int = 50,
    ) -> list[Resource]:
        params: dict[str, Any] = {
            "$expand": expand,
            "resourceType": resource_type,
            "$top": top,
        }
        if only_active:
            params["isDeleted"] = "false"
        resources = self._request_items_paginated(
            "/resources",
            params=params,
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(resources, Resource)

    def update_person_cell_phone(self, person_id: str, cell_phone: str) -> Optional[Person]:
        if self.use_mock:
            plog.info("[MOCK] update_person_cell_phone: returning mock success (use_mock=True)")
            self.conv.log.info("update_person_cell_phone: mock mode, skipping real API call")
            return Person.model_validate(
                {
                    "id": person_id,
                    "cellPhone": cell_phone,
                }
            )

        payload = {"cellPhone": cell_phone}
        response_payload = self._request_json(
            "PATCH", f"/persons/{person_id}", json_payload=payload, timeout=15
        )
        if isinstance(response_payload, dict):
            return Person.model_validate(response_payload)
        return None

    def get_appointment_categories(
        self, top: int = 200, fetch_all_pages: bool = False, max_pages: int = 50
    ) -> list[AppointmentCategory]:
        categories = self._request_items_paginated(
            "/master/appointments/categories",
            params={"$top": top},
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(categories, AppointmentCategory)

    def get_events(
        self, top: int = 200, fetch_all_pages: bool = False, max_pages: int = 50
    ) -> list[Event]:
        events = self._request_items_paginated(
            "/master/events",
            params={"$top": top},
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(events, Event)

    def get_category_events(
        self, category_id: str, top: int = 200, fetch_all_pages: bool = False, max_pages: int = 50
    ) -> list[Event]:
        events = self._request_items_paginated(
            f"/master/appointments/categories/{category_id}/events",
            params={"$top": top},
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(events, Event)

    def get_practice_locations(
        self,
        practice_id: Optional[str] = None,
        only_schedulable: bool = False,
        include_deleted: bool = False,
        top: int = 200,
        fetch_all_pages: bool = False,
        max_pages: int = 50,
    ) -> list[Location]:
        resolved_practice_id = practice_id or self.practice_id
        filters = []
        if not include_deleted:
            filters.append("isDeleted eq false")
        if only_schedulable:
            filters.append("isSchedulable eq true")

        params = {"$top": top}
        filter_clause = self._build_filter(filters)
        if filter_clause:
            params["$filter"] = filter_clause

        if resolved_practice_id:
            path = f"/master/practices/{resolved_practice_id}/locations"
        else:
            path = "/master/locations"
        locations = self._request_items_paginated(
            path,
            params=params,
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(locations, Location)

    def get_practice_payers(
        self,
        practice_id: Optional[str] = None,
        top: int = 200,
        fetch_all_pages: bool = False,
        max_pages: int = 50,
    ) -> list[Payer]:
        resolved_practice_id = practice_id or self.practice_id
        if not resolved_practice_id:
            self.conv.log.warning("get_practice_payers requires practice_id")
            return []

        params = {"$top": top}
        path = f"/master/practices/{resolved_practice_id}/payers"
        payers = self._request_items_paginated(
            path,
            params=params,
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(payers, Payer)

    def get_cancel_reasons(
        self, fetch_all_pages: bool = False, max_pages: int = 50
    ) -> list[ListItem]:
        reasons = self._request_items_paginated(
            "/master/list-items",
            params={"$filter": "type eq 'as_cancel_reason'"},
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(reasons, ListItem)

    def get_reschedule_reasons(
        self, fetch_all_pages: bool = False, max_pages: int = 50
    ) -> list[ListItem]:
        reasons = self._request_items_paginated(
            "/master/list-items",
            params={"$filter": "type eq 'as_resched_reason'"},
            fetch_all_pages=fetch_all_pages,
            max_pages=max_pages,
        )
        return self._parse_model_list(reasons, ListItem)


# ---------------------------------------------------------------------------
# Factory function -- returns MockApiHandler by default for the template
# ---------------------------------------------------------------------------


def _resolve_nextgen_secret_name(conv: Conversation) -> str:
    """
    Resolve the API secret name based on environment.
    Update these placeholder names when connecting to a real NextGen instance.
    """
    env = str(conv.env or "").lower()
    if env == "live":
        return "NextGen Prod API Credentials"
    return "NextGen Sandbox API Credentials"


def get_api_handler(conv: Conversation):
    """
    Factory that returns the appropriate API handler.

    By default returns MockApiHandler (no credentials needed).
    To use the real NextGen API, set the real_time_config flag
    `use_real_api` to true and configure the appropriate secret
    in Agent Studio.
    """
    try:
        _flags = conv.real_time_config.get("flags") or {}
        use_real = _flags.get("use_real_api")
    except Exception:
        use_real = False
    if use_real:
        secret_name = _resolve_nextgen_secret_name(conv)
        return NextGenApiHandler(conv, secret_name)
    return MockApiHandler(conv)


# Backward-compatible alias so existing imports keep working during migration.
get_grace_nextgen_api_handler = get_api_handler


@func_description("Get the NextGen API handler")
def api_handler(conv: Conversation):
    """
    Creates a NextGen API handler.
    Returns MockApiHandler by default (no credentials needed).
    Set real_time_config flag `use_real_api` to true for live API access.
    """
    return get_api_handler(conv)
