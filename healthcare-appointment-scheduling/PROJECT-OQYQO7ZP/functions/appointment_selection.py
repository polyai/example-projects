import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Optional

import plog
from _gen import *  # <AUTO GENERATED>
from functions.nextgen_response_models import Appointment


@func_description("Shared helpers for selecting appointments (cancel/reschedule)")
def appointment_selection(conv: Conversation):
    """Helpers to select and qualify appointments for cancel/reschedule flows."""


# EHR event IDs per appointment type — used when the slot itself has no event_id.
EVENT_ID_BY_APPOINTMENT_TYPE: dict[str, str] = {
    "er_follow_up": "7d15f2f4-20c7-47ab-8900-3bd2ce8ad357",
    "hospital_follow_up": "b3f61b37-9dbc-4f67-aae6-cb377fc8fa23",
    "ill": "0e38e7a7-fcaa-447c-9ff6-b5255bc9c226",
    "recheck": "b5c6d1f8-1820-4c47-ad1a-d6e5e61c8d90",
    "recheck_diabetes": "0216b300-ce77-4c65-a396-7bbe26d9875b",
    "recheck_hypertension": "8e92ae2b-8d15-4ca4-9d9a-4d16ed51282a",
    "recheck_medication": "4370f129-7c3f-453b-ba1c-6ef5330e4640",
}
# Follow-up visit type — self-serve cancel allowed for this type only.
FOLLOW_UP_EVENT_ID = EVENT_ID_BY_APPOINTMENT_TYPE["recheck"]

# Reverse mapping: event_id → human-readable label for disambiguation prompts.
_APPOINTMENT_TYPE_LABELS: dict[str, str] = {
    "er_follow_up": "ER follow-up",
    "hospital_follow_up": "hospital follow-up",
    "ill": "sick visit",
    "recheck": "recheck",
    "recheck_diabetes": "diabetes recheck",
    "recheck_hypertension": "hypertension recheck",
    "recheck_medication": "medication recheck",
}
_EVENT_ID_TO_TYPE = {v.lower(): k for k, v in EVENT_ID_BY_APPOINTMENT_TYPE.items()}


def appointment_type_label(event_id: str | None) -> str:
    """Return a caller-friendly label for an event_id, or 'appointment' as fallback."""
    if not event_id:
        return "appointment"
    appt_type = _EVENT_ID_TO_TYPE.get(str(event_id).lower())
    return _APPOINTMENT_TYPE_LABELS.get(appt_type, "appointment") if appt_type else "appointment"


# ---------------------------------------------------------------------------
# Same-day booking prevention — dental & behavioral health exemptions
# ---------------------------------------------------------------------------

# Event IDs that belong to dental or behavioral health categories.
# Appointments with these event IDs do NOT block same-day booking.
DENTAL_BEHAVIORAL_EXEMPT_EVENT_IDS: set[str] = {
    # Dental events
    "4a46b431-6ea7-453c-a50c-a9db125a3eef",  # Alginate Impressions
    "17b27687-3d9d-4b47-949f-0bc0e9b93bab",  # Crown
    "917993fd-ec03-46f8-8dfd-974081f4e8a2",  # Denture Visit
    "98217e2e-0f20-4fbf-984f-93e13491af32",  # Extraction
    "01394c34-8dfb-4cf0-9fb5-d326413067b1",  # Follow-up (dental)
    "e99d18d1-cff6-4b03-9638-1a5e4e12adb9",  # Limited
    "b8ebfcbc-7e95-4c03-8ddc-b7438ed9cf32",  # Nitrous
    "c075d004-a524-4322-9c11-5ac6fb108b9a",  # NP Walk In
    "ac383d7f-1486-4fbc-bc77-104bd3729569",  # Restorative 30
    "1b7749be-e37c-4b3d-842b-05e1ffa2b88d",  # Restorative 60
    "9183975d-ab46-47f3-b607-7514b7d4acf1",  # Root Canal Treatment 120 Min
    "55080d44-568c-477b-ac75-352ce22f2380",  # Root Canal Treatment 90 Min
    "0a91c283-10bc-4a28-8010-be09fab95b20",  # Surg Extraction
    "bf206f28-414e-4ffd-a7bd-65e210597f16",  # Virtual Visit
    "6a9d86c5-9994-43a4-8d92-519d62d1e94c",  # Meeting
    "2b38b83f-209c-408c-a509-4687d8948dc4",  # Age 1 Visit
    "fc5a3385-84c1-4020-9cad-7365ea9786bd",  # Debridement/Ultrasonic
    "a772ad69-2786-47cf-a707-ce38328e3449",  # NP
    "dbe79fd1-80b2-47d8-9bd6-40caed30fb75",  # NP 45 Mins
    "965b0ef8-86fb-4d49-b4b1-1e11392943f7",  # Perio Scale
    "eb96eaed-cb39-4b4b-8d13-0f8c3a94a101",  # Portable Exam
    "403e2286-2c49-43f1-985e-2d2875167b48",  # Prophy
    "86059f01-0d06-42ee-b1b8-483285036e16",  # Reschedule
    "827640bd-f687-4a60-8f0d-81f81f1dc511",  # Sealants
    "b2185495-af07-4c89-ac8b-1d6d6563f4f3",  # Walk In
    # Behavioral Health events
    "bb166706-491c-458e-9f95-2a0b08d386c7",  # BH Initial VV
    "d6f1d97d-00f7-4cc0-8992-4a9c1d91b14b",  # BH Crisis VV
    "896c73ef-e8a4-49d6-abd7-00879e8178e0",  # BH Revisit VV
    "fd5d5a93-5b4b-4317-bff7-65354ce0d17f",  # Crisis
    "3fc50a3e-a191-4954-b8d8-a5169fc267e1",  # IAP Review
    "25e868d2-5e6b-4f21-bd08-de6b26d64b56",  # Initial
    "21a483d9-d541-4e5e-a09d-6589cf11d9fa",  # Minor Confidential
    "efca083e-9c45-4c04-a8f6-d30dbc75366f",  # Minor Virtual Visit
    "ba1f16cf-f06a-4a6f-94be-9a7095f1fecb",  # Revisit
    "2537778f-d7a6-46bc-b9f5-7c1de9d0a728",  # TOVA
    "71e158fc-347b-4ab6-8195-34a9bab09ad1",  # Autism Diagnostic Observation
}

_SAME_DAY_LOG_PREFIX = "[same_day_booking]: "


def get_blocked_booking_dates(conv: Conversation, start_iso: str, end_iso: str) -> set[str]:
    """
    Return the set of calendar dates (YYYY-MM-DD) within the window where the
    patient already has a non-dental/non-behavioral-health appointment and
    therefore cannot book another appointment.
    """
    from functions.get_grace_nextgen_api_handler import get_grace_nextgen_api_handler

    identified = getattr(conv.state, "identified_patient", None)
    person_id = identified.get("id") if isinstance(identified, dict) else None
    if not person_id:
        plog.info(f"{_SAME_DAY_LOG_PREFIX} no identified_patient; skipping same-day check")
        return set()

    try:
        handler = get_grace_nextgen_api_handler(conv)
        existing = handler.get_person_appointments(
            person_id,
            start_date_iso=start_iso,
            end_date_iso=end_iso,
            top=200,
            fetch_all_pages=True,
            max_pages=20,
        )
    except Exception as e:
        plog.info(f"{_SAME_DAY_LOG_PREFIX} get_person_appointments failed error='{e}'")
        conv.log.error("same-day booking check: appointment fetch failed", error=str(e))
        return set()

    blocked: set[str] = set()
    exempt_lower = {eid.lower() for eid in DENTAL_BEHAVIORAL_EXEMPT_EVENT_IDS}

    for appt in existing:
        if appt.is_cancelled is True:
            continue
        day = normalize_iso_date_prefix(
            str(appt.appointment_date) if appt.appointment_date else None
        )
        if not day:
            continue
        eid = (str(appt.event_id).lower()) if appt.event_id else ""
        if eid not in exempt_lower:
            blocked.add(day)

    plog.info(
        f"{_SAME_DAY_LOG_PREFIX} checked {len(existing)} appointments; "
        f"blocked_dates={sorted(blocked)}",
        is_pii=True,
    )
    return blocked


# ---------------------------------------------------------------------------
# Recall-plan helpers for booking flow slot windowing
# ---------------------------------------------------------------------------

# Recheck appointment types that should be matched against recall plans.
RECHECK_TYPES = {"recheck", "recheck_diabetes", "recheck_hypertension", "recheck_medication"}

# Slots may only be booked on or after the recall return date.
_RECALL_WINDOW_FUTURE_DAYS = 90

_RECALL_LOG_PREFIX = "[recall]: "


@dataclass(frozen=True)
class RecallWindowResult:
    """Result of looking up the recall-based booking window."""

    ok: bool
    start_iso: Optional[str] = None
    end_iso: Optional[str] = None
    expected_return_date: Optional[str] = None
    needs_disambiguation: bool = False
    disambiguation_options: Optional[list[dict]] = None
    resolved_appointment_type: Optional[str] = None


def is_recheck_type(appointment_type: str) -> bool:
    """Return True if the appointment type should use recall-based windowing."""
    return appointment_type in RECHECK_TYPES


def get_recall_window(conv: Conversation, appointment_type: str) -> RecallWindowResult:
    """
    Fetch recall plans for the identified patient, find an active recall whose
    eventId matches the appointment type, and return a ±5-day window around
    expectedReturnDate.

    Returns ok=False if no matching recall is found.
    """
    from functions.get_grace_nextgen_api_handler import get_grace_nextgen_api_handler

    identified = getattr(conv.state, "identified_patient", None)
    person_id = identified.get("id") if isinstance(identified, dict) else None
    if not person_id:
        plog.info(f"{_RECALL_LOG_PREFIX} no identified_patient; cannot fetch recalls")
        return RecallWindowResult(ok=False)

    target_event_id = EVENT_ID_BY_APPOINTMENT_TYPE.get(appointment_type)
    if not target_event_id:
        plog.info(
            f"{_RECALL_LOG_PREFIX} no event_id mapping for appointment_type='{appointment_type}'"
        )
        return RecallWindowResult(ok=False)

    # When the caller says "recheck" generically, also accept sub-type recheck
    # event IDs (diabetes, hypertension, medication) so we match their recall
    # regardless of which specific recheck it is.
    if appointment_type == "recheck":
        target_event_ids = {
            eid.lower() for rt in RECHECK_TYPES if (eid := EVENT_ID_BY_APPOINTMENT_TYPE.get(rt))
        }
    else:
        target_event_ids = {target_event_id.lower()}

    try:
        handler = get_grace_nextgen_api_handler(conv)
        recalls = handler.get_person_recall_plans(person_id, filter_clause="isActive eq true")
    except Exception as e:
        plog.info(f"{_RECALL_LOG_PREFIX} recall plan fetch failed error='{e}'")
        conv.log.error("recall plan fetch failed", error=str(e))
        return RecallWindowResult(ok=False)

    plog.info(
        f"{_RECALL_LOG_PREFIX} fetched {len(recalls)} active recall(s) for person_id_last4="
        f"'{person_id[-4:] if len(person_id) >= 4 else '****'}'"
    )

    # Collect all valid matching recalls with parsed return dates
    now = date.today()
    candidates: list[tuple] = []

    for recall in recalls:
        if not recall.event_id or recall.event_id.lower() not in target_event_ids:
            continue
        if not recall.expected_return_date:
            continue
        try:
            return_date = datetime.fromisoformat(
                recall.expected_return_date.replace("Z", "+00:00")
            ).date()
        except (ValueError, TypeError):
            continue
        candidates.append((recall, return_date))

    if not candidates:
        plog.info(
            f"{_RECALL_LOG_PREFIX} no matching recall for event_id='{target_event_id}' "
            f"(appointment_type='{appointment_type}')"
        )
        return RecallWindowResult(ok=False)

    # When the caller said "recheck" generically, check if the matching recalls
    # span multiple distinct event types — if so, we need to ask which one.
    if appointment_type == "recheck":
        distinct_event_ids = {r.event_id.lower() for r, _ in candidates}
        if len(distinct_event_ids) > 1:
            event_id_to_type = {v.lower(): k for k, v in EVENT_ID_BY_APPOINTMENT_TYPE.items()}
            options = []
            seen_types: set[str] = set()
            for recall, return_date in sorted(candidates, key=lambda x: abs((x[1] - now).days)):
                appt_type = event_id_to_type.get(recall.event_id.lower(), "recheck")
                if appt_type in seen_types:
                    continue
                seen_types.add(appt_type)
                options.append(
                    {
                        "appointment_type": appt_type,
                        "description": recall.event_description or appt_type,
                        "expected_return_date": return_date.isoformat(),
                    }
                )
            plog.info(
                f"{_RECALL_LOG_PREFIX} disambiguation needed: "
                f"{len(options)} distinct recheck types found"
            )
            return RecallWindowResult(
                ok=False,
                needs_disambiguation=True,
                disambiguation_options=options,
            )

    # Single type (or specific sub-type requested) — pick closest to today
    best, best_return_date = min(candidates, key=lambda x: abs((x[1] - now).days))

    # When the caller said generic "recheck" but all recalls map to one specific
    # subtype, resolve to that subtype so metrics and state reflect the actual type.
    resolved_type: str | None = None
    if appointment_type == "recheck":
        distinct_event_ids = {r.event_id.lower() for r, _ in candidates}
        if len(distinct_event_ids) == 1:
            specific = _EVENT_ID_TO_TYPE.get(next(iter(distinct_event_ids)))
            if specific and specific != "recheck":
                resolved_type = specific
                plog.info(f"{_RECALL_LOG_PREFIX} generic recheck resolved to '{resolved_type}'")

    window_start = best_return_date
    window_end = best_return_date + timedelta(days=_RECALL_WINDOW_FUTURE_DAYS)
    start_iso = window_start.strftime("%Y-%m-%dT00:00:00")
    end_iso = window_end.strftime("%Y-%m-%dT23:59:59")

    plog.info(
        f"{_RECALL_LOG_PREFIX} recall matched: event='{best.event_description}' "
        f"expected_return='{best_return_date}' window=['{start_iso}', '{end_iso}']",
        is_pii=True,
    )

    return RecallWindowResult(
        ok=True,
        start_iso=start_iso,
        end_iso=end_iso,
        expected_return_date=best_return_date.isoformat(),
        resolved_appointment_type=resolved_type,
    )


def normalize_iso_date_prefix(value: Optional[str]) -> Optional[str]:
    """Return YYYY-MM-DD prefix from an ISO-like datetime string, or None."""
    if value is None:
        return None
    s = str(value).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def parse_utc_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse appointment API datetime to an aware UTC datetime (best effort)."""
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def is_active_not_cancelled(appointment: Appointment) -> bool:
    return appointment.is_cancelled is not True


def is_already_rescheduled(appointment: Appointment) -> bool:
    return appointment.is_rescheduled is True


def is_future_appointment(appointment: Appointment, now_utc: datetime) -> bool:
    # appointmentDate is date-only (T00:00:00), so compare dates not datetimes
    # to avoid filtering out same-day appointments.
    dt = parse_utc_datetime(appointment.appointment_date)
    if dt is None:
        return False
    return dt.date() >= now_utc.date()


def filter_upcoming_active(
    appointments: list[Appointment], now_utc: Optional[datetime] = None
) -> list[Appointment]:
    """Non-cancelled appointments strictly after ``now_utc`` (default: current UTC)."""
    now = now_utc or datetime.now(UTC)
    return [a for a in appointments if is_active_not_cancelled(a) and is_future_appointment(a, now)]


def is_follow_up_appointment(appointment: Appointment) -> bool:
    eid = appointment.event_id
    if not eid:
        return False
    _known = {v.lower() for v in EVENT_ID_BY_APPOINTMENT_TYPE.values()}
    return str(eid).lower() in _known


def normalize_entity_date_to_yyyy_mm_dd(value: object) -> Optional[str]:
    """Normalize a date entity (date object or spoken string) to YYYY-MM-DD."""
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            return isoformat()[:10]
        except Exception:
            pass
    s = str(value).strip()
    if not s:
        return None
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    digits = re.sub(r"\D", "", s)
    if len(digits) == 8:
        y1 = int(digits[:4])
        if 1900 <= y1 <= 2100:
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        return f"{digits[4:8]}-{digits[:2]}-{digits[2:4]}"
    return s[:10] if len(s) >= 10 else None


_MONTH_NAME_TO_NUM: tuple[tuple[str, int], ...] = (
    ("january", 1),
    ("february", 2),
    ("march", 3),
    ("april", 4),
    ("may", 5),
    ("june", 6),
    ("july", 7),
    ("august", 8),
    ("september", 9),
    ("october", 10),
    ("november", 11),
    ("december", 12),
    ("jan", 1),
    ("feb", 2),
    ("mar", 3),
    ("apr", 4),
    ("jun", 6),
    ("jul", 7),
    ("aug", 8),
    ("sep", 9),
    ("oct", 10),
    ("nov", 11),
    ("dec", 12),
)

# Monday=0 .. Sunday=6 (datetime.weekday())
_WEEKDAY_NAME_TO_INDEX: tuple[tuple[str, int], ...] = (
    ("monday", 0),
    ("tuesday", 1),
    ("wednesday", 2),
    ("thursday", 3),
    ("friday", 4),
    ("saturday", 5),
    ("sunday", 6),
)


def last_user_text_from_history(conv: Conversation) -> Optional[str]:
    """Most recent non-empty user turn, or None."""
    for event in reversed(conv.history):
        if event.role == "user" and event.text and str(event.text).strip():
            return str(event.text).strip()
    return None


def calendar_day_from_relative_phrases(text: str, today: date) -> Optional[str]:
    """
    Map phrases like 'tomorrow' / 'today' to YYYY-MM-DD using the given anchor day (UTC calendar).
    Same idea as therapy-partners _iso_date_from_relative_nomination, without local timezone.
    """
    raw = text.strip().lower()
    if not raw:
        return None
    if re.search(r"\bday after tomorrow\b", raw):
        return (today + timedelta(days=2)).isoformat()
    if re.search(r"\btomorrow\b", raw):
        return (today + timedelta(days=1)).isoformat()
    if re.search(r"\b(today|tonight)\b", raw):
        return today.isoformat()
    return None


def _appointment_day_prefix(ap: Appointment) -> Optional[str]:
    return normalize_iso_date_prefix(str(ap.appointment_date) if ap.appointment_date else None)


def unique_calendar_day_from_weekday_in_appointments(
    text: str, appointments: list[Appointment], today: date
) -> Optional[str]:
    """
    If the user names a weekday and exactly one loaded appointment falls on that weekday
    within the next 31 days (starting today), return that calendar day.
    """
    raw = text.strip().lower()
    if not raw or not appointments:
        return None
    for name, wk in _WEEKDAY_NAME_TO_INDEX:
        if name not in raw:
            continue
        hits: list[str] = []
        for offset in range(0, 32):
            cand = today + timedelta(days=offset)
            if cand.weekday() != wk:
                continue
            iso = cand.isoformat()
            if match_appointments_on_calendar_day(appointments, iso):
                hits.append(iso)
        if len(hits) == 1:
            return hits[0]
        return None
    return None


def unique_calendar_day_from_month_day_in_appointments(
    text: str, appointments: list[Appointment]
) -> Optional[str]:
    """
    If the user gives month+day (spoken or numeric) and exactly one upcoming appointment
    matches that month and day, return its YYYY-MM-DD.
    """
    if not text or not appointments:
        return None
    raw_lower = text.strip().lower()

    def _month_day_from_prefix(p: str) -> tuple[int, int] | None:
        if len(p) < 10:
            return None
        try:
            return int(p[5:7]), int(p[8:10])
        except ValueError:
            return None

    for name, mnum in _MONTH_NAME_TO_NUM:
        if name not in raw_lower:
            continue
        dm = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\b", raw_lower)
        if not dm:
            continue
        d = int(dm.group(1))
        matched_days: list[str] = []
        for a in appointments:
            p = _appointment_day_prefix(a)
            md = _month_day_from_prefix(p) if p else None
            if md and md[0] == mnum and md[1] == d:
                matched_days.append(p)
        uniq = {x for x in matched_days if x}
        if len(uniq) == 1:
            return next(iter(uniq))

    m_may = re.search(r"\bmay\s+(\d{1,2})(?:st|nd|rd|th)?\b", raw_lower)
    if m_may:
        d = int(m_may.group(1))
        matched_days = []
        for a in appointments:
            p = _appointment_day_prefix(a)
            md = _month_day_from_prefix(p) if p else None
            if md and md[0] == 5 and md[1] == d:
                matched_days.append(p)
        uniq = {x for x in matched_days if x}
        if len(uniq) == 1:
            return next(iter(uniq))

    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})\b(?:\s*/\s*(\d{2,4}))?\b", raw_lower)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        for month_guess, day_guess in ((a, b), (b, a)):
            if not (1 <= month_guess <= 12 and 1 <= day_guess <= 31):
                continue
            matched_days = []
            for ap in appointments:
                p = _appointment_day_prefix(ap)
                md = _month_day_from_prefix(p) if p else None
                if md and md[0] == month_guess and md[1] == day_guess:
                    matched_days.append(p)
            uniq = {x for x in matched_days if x}
            if len(uniq) == 1:
                return next(iter(uniq))
    return None


def resolve_cancel_appointment_calendar_day(
    *,
    last_user_text: Optional[str],
    entity_value: object,
    appointments: list[Appointment],
    today_utc: date,
) -> Optional[str]:
    """
    Decide YYYY-MM-DD for cancel matching: prefer deterministic parsing of the last user turn,
    then disambiguate against loaded appointments, then the entity extractor.

    Order: relative phrases -> weekday+unique appt -> month/day+unique appt -> entity -> last user string.
    """
    raw = (last_user_text or "").strip()
    if raw:
        rel = calendar_day_from_relative_phrases(raw, today_utc)
        if rel:
            return rel
        wk = unique_calendar_day_from_weekday_in_appointments(raw, appointments, today_utc)
        if wk:
            return wk
        md = unique_calendar_day_from_month_day_in_appointments(raw, appointments)
        if md:
            return md

    ent = normalize_entity_date_to_yyyy_mm_dd(entity_value)
    if ent:
        return ent

    if raw:
        return normalize_entity_date_to_yyyy_mm_dd(raw)
    return None


def find_appointments_by_month_day(
    appointments: list[Appointment], month: int, day: int
) -> list[Appointment]:
    """Match loaded appointments by calendar month and day (UTC date prefix from API)."""
    result: list[Appointment] = []
    for a in appointments:
        p = normalize_iso_date_prefix(str(a.appointment_date) if a.appointment_date else None)
        if not p or len(p) < 10:
            continue
        try:
            if int(p[5:7]) == month and int(p[8:10]) == day:
                result.append(a)
        except ValueError:
            continue
    return result


def resolve_cancel_appointments_from_date_parts(
    appointments: list[Appointment],
    day_str: str,
    month_str: str,
    year_str: str,
) -> tuple[list[Appointment], str | None]:
    """
    Match appointments from structured day/month/year strings (therapy-partners pattern).

    When year is N/A, match by month+day only against loaded appointments.

    Returns (matches, error_key). error_key: missing_day_or_month, invalid_components, or None.
    """
    day_str = str(day_str).strip()
    month_str = str(month_str).strip()
    year_str = str(year_str).strip()
    if not day_str or day_str.lower() in ("na", "n/a"):
        return [], "missing_day_or_month"
    if not month_str or month_str.lower() in ("na", "n/a"):
        return [], "missing_day_or_month"
    try:
        day_i = int(day_str)
        month_i = int(month_str)
    except ValueError:
        return [], "invalid_components"
    if not (1 <= month_i <= 12 and 1 <= day_i <= 31):
        return [], "invalid_components"

    if not year_str or year_str.lower() in ("na", "n/a"):
        return find_appointments_by_month_day(appointments, month_i, day_i), None

    try:
        year_i = int(year_str)
    except ValueError:
        return [], "invalid_components"
    try:
        resolved = date(year_i, month_i, day_i).isoformat()
    except ValueError:
        return [], "invalid_components"
    return match_appointments_on_calendar_day(appointments, resolved), None


def match_appointments_on_calendar_day(
    appointments: list[Appointment], calendar_day_yyyy_mm_dd: str
) -> list[Appointment]:
    """Return appointments whose ``appointmentDate`` falls on the given calendar day (YYYY-MM-DD)."""
    target = normalize_iso_date_prefix(calendar_day_yyyy_mm_dd)
    if not target:
        return []
    matched: list[Appointment] = []
    for a in appointments:
        aprefix = normalize_iso_date_prefix(str(a.appointment_date) if a.appointment_date else None)
        if aprefix == target:
            matched.append(a)
    return matched
