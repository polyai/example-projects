"""Fetch open appointment slots into state for booking and rescheduling flows."""

from _gen import *  # <AUTO GENERATED>
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Optional

import plog
from functions.get_grace_nextgen_api_handler import get_grace_nextgen_api_handler

_LOG_PREFIX = "[fetch_available_slots]: "


@dataclass(frozen=True)
class FetchAvailableSlotsResult:
    """Result of fetching available slots."""

    ok: bool
    utterance: str


def fetch_booking_slots_for_state(
    conv: Conversation,
    start_override: Optional[str] = None,
    end_override: Optional[str] = None,
) -> FetchAvailableSlotsResult:
    """Fetch open appointment slots and store in ``conv.state.booking_available_slots``.

    By default fetches the next 90 days. Returns ``ok=True`` when at least one
    slot was found.
    """
    now = datetime.now(UTC)
    start_iso = start_override or now.strftime("%Y-%m-%dT00:00:00")
    end_iso = end_override or (now + timedelta(days=90)).strftime("%Y-%m-%dT23:59:59")
    plog.info(f"{_LOG_PREFIX} [booking] start_iso='{start_iso}' end_iso='{end_iso}'")

    resource_id = getattr(conv.state, "patient_resource_id", None) or None

    try:
        handler = get_grace_nextgen_api_handler(conv)
        raw_slots = handler.search_appointment_slots(
            start_date_iso=start_iso,
            end_date_iso=end_iso,
            resource_id=resource_id,
            only_open_slots=True,
            top=150,
        )
        plog.info(f"{_LOG_PREFIX} [booking] raw_slot_count={len(raw_slots)}")
    except Exception as e:
        plog.info(
            f"{_LOG_PREFIX} [booking] search_appointment_slots failed error='{e}'"
        )
        conv.log.error("Booking slot fetch failed", error=str(e))
        return FetchAvailableSlotsResult(
            ok=False,
            utterance="We couldn't look up available times right now. Please try again later.",
        )

    dumped = [s.model_dump(mode="json") for s in raw_slots]
    conv.state.booking_available_slots = dumped
    conv.write_metric("BOOKING_FLOW_SLOTS_LOADED", len(raw_slots))

    if not raw_slots:
        plog.info(f"{_LOG_PREFIX} [booking] no slots available")
        return FetchAvailableSlotsResult(
            ok=False,
            utterance="I'm not seeing any available appointment times right now.",
        )

    plog.info(f"{_LOG_PREFIX} [booking] success slot_count={len(raw_slots)}")
    return FetchAvailableSlotsResult(ok=True, utterance="")


def fetch_available_slots_for_state(
    conv: Conversation,
    start_override: Optional[str] = None,
    end_override: Optional[str] = None,
) -> FetchAvailableSlotsResult:
    """Fetch open appointment slots for the reschedule flow.

    Stores results in ``conv.state.reschedule_available_slots``.
    Returns ``ok=True`` when at least one slot was found.
    """
    now = datetime.now(UTC)
    start_iso = start_override or now.strftime("%Y-%m-%dT00:00:00")
    end_iso = end_override or (now + timedelta(days=90)).strftime("%Y-%m-%dT23:59:59")
    plog.info(f"{_LOG_PREFIX} [reschedule] start_iso='{start_iso}' end_iso='{end_iso}'")

    resource_id = getattr(conv.state, "patient_resource_id", None) or None

    try:
        handler = get_grace_nextgen_api_handler(conv)
        raw_slots = handler.search_appointment_slots(
            start_date_iso=start_iso,
            end_date_iso=end_iso,
            resource_id=resource_id,
            only_open_slots=True,
            top=150,
        )
        plog.info(f"{_LOG_PREFIX} [reschedule] raw_slot_count={len(raw_slots)}")
    except Exception as e:
        plog.info(
            f"{_LOG_PREFIX} [reschedule] search_appointment_slots failed error='{e}'"
        )
        conv.log.error("Reschedule slot fetch failed", error=str(e))
        return FetchAvailableSlotsResult(
            ok=False,
            utterance="We couldn't look up available times right now. Please try again later.",
        )

    dumped = [s.model_dump(mode="json") for s in raw_slots]
    conv.state.reschedule_available_slots = dumped
    conv.write_metric("RESCHEDULE_FLOW_SLOTS_LOADED", len(raw_slots))

    if not raw_slots:
        plog.info(f"{_LOG_PREFIX} [reschedule] no slots available")
        return FetchAvailableSlotsResult(
            ok=False,
            utterance=(
                "I'm not seeing any available follow-up slots in the next 90 days. "
                "Let me transfer you to someone who can help find a time."
            ),
        )

    plog.info(f"{_LOG_PREFIX} [reschedule] success slot_count={len(raw_slots)}")
    return FetchAvailableSlotsResult(ok=True, utterance="")


@func_description("Fetch available appointment slots (utility module).")
def fetch_available_slots(conv: Conversation) -> None:
    """Platform entry point for this module (helpers are imported directly)."""
    plog.info(f"{_LOG_PREFIX} invoked")
