"""Fetch open follow-up appointment slots into state for slot-offering steps."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Optional

import plog
from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import get_blocked_booking_dates, normalize_iso_date_prefix
from functions.get_grace_nextgen_api_handler import get_grace_nextgen_api_handler
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import _parse_datetime_like, filter_slots_by_lead_time


def get_providers_from_same_group(conv, pcp_id: str) -> list[dict]:
    """Stub: no provider grouping in the template."""
    return []


# TODO(HP-31181): Once we have prod API access, replace this category_id filter with an
# event_id filter using FOLLOW_UP_EVENT_ID from appointment_selection.py. The sandbox
# environment doesn't have slots with the correct event_id, so we're temporarily scoping
# by category instead.
_FOLLOW_UP_CATEGORY_ID = "d49517d3-725f-4f54-8614-aac4f3abafb1"
FPIM_SD_CATEGORY_ID = "20ba449e-17f7-41b8-94e8-faed9474a600"
CSS_PRESCHEDULE_CATEGORY_ID = "1ea686ca-c345-408c-8173-e2f358a934d3"
CSS_SAME_DAY_CATEGORY_ID = "58dd34ec-df39-420b-9be0-09004e6a3394"


@dataclass(frozen=True)
class FetchAvailableSlotsResult:
    """Result of fetching available slots."""

    ok: bool
    utterance: str


_LOG_PREFIX = "[fetch_available_slots]: "


def _fetch_neighborhood_slots(conv, handler, primary_resource_id, start_iso, end_iso, category_id):
    """Fetch slots from neighborhood providers (same care-team group), excluding the primary."""
    pcp_id = getattr(conv.state, "patient_primary_care_provider_id", None) or None
    if not pcp_id:
        return []
    neighborhood = get_providers_from_same_group(conv, pcp_id)
    nbr_resource_ids = [
        p.get("resource_id")
        for p in neighborhood
        if p.get("resource_id") and p.get("resource_id") != primary_resource_id
    ]
    plog.info(f"{_LOG_PREFIX} trying {len(nbr_resource_ids)} neighborhood resources")
    all_slots = []
    for nbr_rid in nbr_resource_ids:
        try:
            nbr_slots = handler.search_appointment_slots(
                start_date_iso=start_iso,
                end_date_iso=end_iso,
                category_id=category_id,
                resource_id=nbr_rid,
                only_open_slots=True,
                top=150,
            )
            all_slots.extend(nbr_slots)
        except Exception as nbr_e:
            plog.info(
                f"{_LOG_PREFIX} neighborhood fetch failed resource_id='{nbr_rid}' error='{nbr_e}'"
            )
    return all_slots


def _slot_start_utc_aware(slot: AppointmentSlot) -> Optional[datetime]:
    """Parse slot start and normalize to UTC-aware for ordering and merge comparison."""
    parsed = _parse_datetime_like(str(slot.start_date or ""))
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _merge_consecutive_slots_for_language_barrier(
    slots: list[AppointmentSlot],
) -> list[AppointmentSlot]:
    """Combine consecutive 15-minute slots (same resource and location) into 30-minute slots.

    The EHR often returns 15-minute increments; language-barrier bookings need 30 minutes.
    Slots with ``duration_minutes >= 30`` are kept as-is. Pairs of 15-minute slots where
    the second starts exactly 15 minutes after the first are merged (greedy, earliest first).
    Each 15-minute row participates in at most one pair. Unpaired 15-minute slots are omitted.
    """
    long_slots: list[AppointmentSlot] = []
    short_by_key: dict[tuple[Optional[str], Optional[str]], list[AppointmentSlot]] = {}

    for slot in slots:
        d = slot.duration_minutes
        if d is not None and d >= 30:
            long_slots.append(slot)
            continue
        if d != 15:
            continue
        key = (slot.resource_id, slot.location_id)
        short_by_key.setdefault(key, []).append(slot)

    merged: list[AppointmentSlot] = []
    merge_pair_count = 0

    for group in short_by_key.values():
        dated: list[tuple[datetime, AppointmentSlot]] = []
        for s in group:
            norm = _slot_start_utc_aware(s)
            if norm is None:
                continue
            dated.append((norm, s))
        dated.sort(key=lambda t: (t[0], str(t[1].start_date or "")))

        i = 0
        while i < len(dated):
            if i + 1 >= len(dated):
                break
            a_dt, a_slot = dated[i]
            b_dt, b_slot = dated[i + 1]
            if b_dt == a_dt + timedelta(minutes=15):
                merged.append(a_slot.model_copy(update={"duration_minutes": 30}))
                merge_pair_count += 1
                i += 2
            else:
                i += 1

    out = long_slots + merged
    _far_future = datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC)

    def _sort_key(s: AppointmentSlot) -> tuple[datetime, str]:
        p = _slot_start_utc_aware(s)
        return (p if p is not None else _far_future, str(s.start_date or ""))

    out.sort(key=_sort_key)

    pre = len(slots)
    post = len(out)
    plog.info(
        f"{_LOG_PREFIX} [booking] language_barrier merge: "
        f"input_slots={pre} kept_ge_30={len(long_slots)} merged_pairs={merge_pair_count} "
        f"output_slots={post} (key_groups={len(short_by_key)})"
    )
    return out


def filter_slots_for_extended_appointment(
    slots: list[AppointmentSlot],
) -> list[AppointmentSlot]:
    """Keep only slots starting at :00 or :45 past the hour (valid first-slot times for extended bookings)."""
    _VALID_MINUTES = {0, 45}
    result = []
    for slot in slots:
        parsed = _slot_start_utc_aware(slot)
        if parsed is not None and parsed.minute in _VALID_MINUTES:
            result.append(slot)
    plog.info(
        f"{_LOG_PREFIX} [booking] extended_appointment filter: "
        f"{len(slots)} -> {len(result)} slots (kept :00/:45 starts)"
    )
    return result


def _apply_booking_filters(raw_slots, now, language_barrier, blocked_dates):
    """Apply lead-time, language-barrier, and same-day booking filters to raw slots."""
    slots = filter_slots_by_lead_time(raw_slots, now)
    plog.info(f"{_LOG_PREFIX} [booking] after_lead_time_filter slot_count={len(slots)}")

    if language_barrier:
        pre_merge = len(slots)
        slots = _merge_consecutive_slots_for_language_barrier(slots)
        plog.info(
            f"{_LOG_PREFIX} [booking] language_barrier: "
            f"{pre_merge} -> {len(slots)} slots after 15+15 merge to 30 min"
        )

    if blocked_dates:
        pre_filter_count = len(slots)
        slots = [
            s
            for s in slots
            if normalize_iso_date_prefix(str(s.start_date) if s.start_date else None)
            not in blocked_dates
        ]
        plog.info(
            f"{_LOG_PREFIX} [booking] same-day filter: "
            f"{pre_filter_count} -> {len(slots)} slots "
            f"(blocked_dates={sorted(blocked_dates)})"
        )

    return slots


def fetch_available_slots_for_state(
    conv: Conversation,
    start_override: Optional[str] = None,
    end_override: Optional[str] = None,
) -> FetchAvailableSlotsResult:
    """
    Fetch open follow-up appointment slots and store them in
    ``conv.state.reschedule_available_slots`` (list of JSON-serializable dicts).

    By default fetches the next 90 days.  Pass ``start_override`` / ``end_override``
    (ISO datetime strings) to constrain to a specific window (e.g. recall or
    discharge-date window).

    If the patient's primary provider has no slots, falls back to other providers
    in the same neighborhood group and sets ``conv.state.reschedule_neighborhood_fallback``.

    Call this before transitioning to a slot-offering step.

    Returns ``ok=True`` only when at least one slot was found.
    """
    now = datetime.now(UTC)
    start_iso = start_override or now.strftime("%Y-%m-%dT00:00:00")
    end_iso = end_override or (now + timedelta(days=90)).strftime("%Y-%m-%dT23:59:59")
    plog.info(f"{_LOG_PREFIX} start_iso='{start_iso}' end_iso='{end_iso}'")

    resource_id = getattr(conv.state, "patient_resource_id", None) or None
    plog.info(f"{_LOG_PREFIX} [reschedule] resource_id='{resource_id}'")
    if not resource_id:
        conv.log.warning(
            "fetch_available_slots_for_state: no patient_resource_id in state; fetching unfiltered slots"
        )

    try:
        handler = get_grace_nextgen_api_handler(conv)
        raw_slots = handler.search_appointment_slots(
            start_date_iso=start_iso,
            end_date_iso=end_iso,
            # TODO(HP-31181): replace category_id with event_id filter (FOLLOW_UP_EVENT_ID)
            # once prod API access is available.
            category_id=_FOLLOW_UP_CATEGORY_ID,
            resource_id=resource_id,
            only_open_slots=True,
            top=150,
        )
        plog.info(f"{_LOG_PREFIX} [reschedule] raw_slot_count={len(raw_slots)}")

        # Neighborhood fallback — triggered when primary resource_id was used but returned empty
        neighborhood_tried = False
        if not raw_slots and resource_id:
            neighborhood_tried = True
            plog.info(
                f"{_LOG_PREFIX} [reschedule] no slots found for primary provider resource_id='{resource_id}'"
            )
            conv.log.info(
                "Reschedule slot fetch: no slots available with patient's primary provider",
                resource_id=resource_id,
            )
            raw_slots = _fetch_neighborhood_slots(
                conv, handler, resource_id, start_iso, end_iso, _FOLLOW_UP_CATEGORY_ID
            )
            if raw_slots:
                conv.state.reschedule_neighborhood_fallback = True
                plog.info(
                    f"{_LOG_PREFIX} [reschedule] neighborhood fallback active; {len(raw_slots)} slots found"
                )

    except Exception as e:
        plog.info(f"{_LOG_PREFIX} search_appointment_slots failed error='{e}'")
        conv.log.error("Reschedule slot fetch: search_appointment_slots failed", error=str(e))
        return FetchAvailableSlotsResult(
            ok=False,
            utterance="We couldn't look up available times right now. Please try again later.",
        )

    # Exclude same-day slots that start within the next 60 minutes
    slots = filter_slots_by_lead_time(raw_slots, now)
    plog.info(f"{_LOG_PREFIX} after_lead_time_filter slot_count={len(slots)}")

    # Post-filter neighborhood fallback — triggered when the primary provider had
    # raw slots but all were removed by the lead-time filter.
    if not slots and resource_id and not neighborhood_tried:
        plog.info(
            f"{_LOG_PREFIX} [reschedule] primary slots all filtered out; trying neighborhood providers"
        )
        conv.log.info(
            "Reschedule slot fetch: no slots available with patient's primary provider after filtering",
            resource_id=resource_id,
        )
        try:
            nbr_raw = _fetch_neighborhood_slots(
                conv, handler, resource_id, start_iso, end_iso, _FOLLOW_UP_CATEGORY_ID
            )
            if nbr_raw:
                slots = filter_slots_by_lead_time(nbr_raw, now)
                if slots:
                    conv.state.reschedule_neighborhood_fallback = True
                    plog.info(
                        f"{_LOG_PREFIX} [reschedule] neighborhood fallback active (post-filter); "
                        f"{len(slots)} slots found"
                    )
        except Exception as nbr_e:
            plog.info(
                f"{_LOG_PREFIX} [reschedule] post-filter neighborhood fetch failed error='{nbr_e}'"
            )

    dumped = [s.model_dump(mode="json") for s in slots]
    conv.state.reschedule_available_slots = dumped
    conv.write_metric("RESCHEDULE_FLOW_SLOTS_LOADED", len(slots))
    conv.log.info("Reschedule flow: loaded available slots", count=len(slots))

    if not slots:
        plog.info(f"{_LOG_PREFIX} no follow-up slots available in 90-day window")
        return FetchAvailableSlotsResult(
            ok=False,
            utterance=(
                "I'm not seeing any available follow-up slots in the next 90 days. "
                "Let me transfer you to someone who can help find a time."
            ),
        )

    plog.info(f"{_LOG_PREFIX} success slot_count={len(slots)}")
    return FetchAvailableSlotsResult(ok=True, utterance="")


def fetch_booking_slots_for_state(
    conv: Conversation,
    start_override: Optional[str] = None,
    end_override: Optional[str] = None,
    category_id_override: Optional[str] = None,
    skip_blocked_dates: bool = False,
) -> FetchAvailableSlotsResult:
    """
    Fetch open follow-up appointment slots and store them in
    ``conv.state.booking_available_slots`` (list of JSON-serializable dicts).

    By default fetches the next 90 days. Pass ``start_override`` / ``end_override``
    (ISO datetime strings) to constrain to a specific window (e.g. the 83–91 day
    diabetes recheck window).

    Pass ``category_id_override`` to search a different appointment category
    instead of the default follow-up category.

    If the patient's primary provider has no slots in the window, falls back to other
    providers in the same neighborhood group and sets
    ``conv.state.booking_neighborhood_fallback = True``.

    Call this before transitioning to a slot-offering step in the Booking Flow.

    Returns ``ok=True`` only when at least one slot was found.
    """
    now = datetime.now(UTC)
    start_iso = start_override or now.strftime("%Y-%m-%dT00:00:00")
    end_iso = end_override or (now + timedelta(days=90)).strftime("%Y-%m-%dT23:59:59")
    effective_category = category_id_override or _FOLLOW_UP_CATEGORY_ID
    plog.info(
        f"{_LOG_PREFIX} [booking] start_iso='{start_iso}' end_iso='{end_iso}' "
        f"category_id='{effective_category}'"
    )

    # Persist the effective slot search context for downstream steps (e.g. decline fallback).
    conv.state.booking_slot_search_start_iso = start_iso
    conv.state.booking_slot_search_end_iso = end_iso
    conv.state.booking_slot_search_category_id = effective_category

    resource_id = getattr(conv.state, "patient_resource_id", None) or None
    plog.info(f"{_LOG_PREFIX} [booking] resource_id='{resource_id}'")
    if not resource_id:
        conv.log.warning(
            "fetch_booking_slots_for_state: no patient_resource_id in state; fetching unfiltered slots"
        )

    try:
        handler = get_grace_nextgen_api_handler(conv)
        raw_slots = handler.search_appointment_slots(
            start_date_iso=start_iso,
            end_date_iso=end_iso,
            category_id=effective_category,
            resource_id=resource_id,
            only_open_slots=True,
            top=150,
        )
        plog.info(f"{_LOG_PREFIX} [booking] raw_slot_count={len(raw_slots)}")

        # Neighborhood fallback — triggered when primary resource_id was used but returned empty
        neighborhood_tried = False
        if not raw_slots and resource_id:
            neighborhood_tried = True
            plog.info(
                f"{_LOG_PREFIX} [booking] no slots found for primary provider resource_id='{resource_id}'"
            )
            conv.log.info(
                "Booking slot fetch: no slots available with patient's primary provider",
                resource_id=resource_id,
            )
            raw_slots = _fetch_neighborhood_slots(
                conv, handler, resource_id, start_iso, end_iso, effective_category
            )
            if raw_slots:
                conv.state.booking_neighborhood_fallback = True
                plog.info(
                    f"{_LOG_PREFIX} [booking] neighborhood fallback active; {len(raw_slots)} slots found"
                )

    except Exception as e:
        plog.info(f"{_LOG_PREFIX} [booking] search_appointment_slots failed error='{e}'")
        conv.log.error("Booking slot fetch: search_appointment_slots failed", error=str(e))
        return FetchAvailableSlotsResult(
            ok=False,
            utterance="We couldn't look up available times right now. Please try again later.",
        )

    language_barrier = getattr(conv.state, "patient_language_barrier", False)
    blocked_dates = (
        set() if skip_blocked_dates else get_blocked_booking_dates(conv, start_iso, end_iso)
    )
    slots = _apply_booking_filters(raw_slots, now, language_barrier, blocked_dates)

    # Post-filter neighborhood fallback — triggered when the primary provider had
    # raw slots but all were removed by filtering (lead time, same-day block, etc.)
    if not slots and resource_id and not neighborhood_tried:
        plog.info(
            f"{_LOG_PREFIX} [booking] primary slots all filtered out; trying neighborhood providers"
        )
        conv.log.info(
            "Booking slot fetch: no slots available with patient's primary provider after filtering",
            resource_id=resource_id,
        )
        try:
            nbr_raw = _fetch_neighborhood_slots(
                conv, handler, resource_id, start_iso, end_iso, effective_category
            )
            if nbr_raw:
                slots = _apply_booking_filters(nbr_raw, now, language_barrier, blocked_dates)
                if slots:
                    conv.state.booking_neighborhood_fallback = True
                    plog.info(
                        f"{_LOG_PREFIX} [booking] neighborhood fallback active (post-filter); "
                        f"{len(slots)} slots found"
                    )
        except Exception as nbr_e:
            plog.info(
                f"{_LOG_PREFIX} [booking] post-filter neighborhood fetch failed error='{nbr_e}'"
            )

    dumped = [s.model_dump(mode="json") for s in slots]
    conv.state.booking_available_slots = dumped
    conv.write_metric("BOOKING_FLOW_SLOTS_LOADED", len(slots))
    conv.log.info("Booking flow: loaded available slots", count=len(slots))

    if not slots:
        plog.info(f"{_LOG_PREFIX} [booking] no follow-up slots available in window")
        return FetchAvailableSlotsResult(
            ok=False,
            utterance=(
                "I'm not seeing any available appointment times in the next 90 days. "
                "Let me transfer you to someone who can help find a time."
            ),
        )

    plog.info(f"{_LOG_PREFIX} [booking] success slot_count={len(slots)}")
    return FetchAvailableSlotsResult(ok=True, utterance="")


@func_description(
    "Fetch available appointment slots for rescheduling (utility module; not called directly by LLM)."
)
def fetch_available_slots(conv: Conversation) -> None:
    """Platform entry point for this module (helpers are imported directly)."""
    log_prefix = "[fetch_available_slots.fetch_available_slots]: "
    plog.info(f"{log_prefix} invoked")
