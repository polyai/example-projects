"""Load upcoming appointments into state for the cancel flow (before entering Cancel Flow)."""

from _gen import *  # <AUTO GENERATED>
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import plog
from functions.appointment_selection import filter_upcoming_active
from functions.get_grace_nextgen_api_handler import get_grace_nextgen_api_handler
from functions.nextgen_response_models import Appointment


@dataclass(frozen=True)
class LoadCancelAppointmentsResult:
    """Result of loading appointments for cancel flow."""

    ok: bool
    utterance: str


_LOG_PREFIX = "[load_cancel_upcoming_appointments]: "


def load_cancel_upcoming_appointments_for_state(
    conv: Conversation,
) -> LoadCancelAppointmentsResult:
    """
    Fetch upcoming visits for ``conv.state.identified_patient`` and store them on
    ``conv.state.cancel_upcoming_appointments`` (JSON-serializable dicts).

    Call this **before** ``goto_flow("Cancel Flow")`` so the flow can start at Resolve Appointment.

    Returns ``ok=True`` only when at least one upcoming appointment was loaded.
    """
    patient = getattr(conv.state, "identified_patient", None)
    pid: str | None = None
    if isinstance(patient, dict):
        pid = patient.get("id")
    elif patient is not None:
        pid = getattr(patient, "id", None)
    if not patient or not pid:
        plog.info(
            f"{_LOG_PREFIX} missing identified_patient or id", has_patient=bool(patient)
        )
        conv.log.warning("Cancel flow preload: no identified_patient on state")
        return LoadCancelAppointmentsResult(
            ok=False,
            utterance=(
                "We need to verify who you are before we can cancel a visit. "
                "Please try again after verifying your account."
            ),
        )

    person_id = str(pid)
    now = datetime.now(UTC)
    start_iso = now.strftime("%Y-%m-%dT00:00:00")
    end_iso = (now + timedelta(days=365)).strftime("%Y-%m-%dT23:59:59")
    plog.info(
        f"{_LOG_PREFIX} person_id_last4='{person_id[-4:] if len(person_id) >= 4 else '****'}' "
        f"start_iso='{start_iso}' end_iso='{end_iso}'"
    )

    try:
        handler = get_grace_nextgen_api_handler(conv)
        raw = handler.get_person_appointments(
            person_id,
            start_date_iso=start_iso,
            end_date_iso=end_iso,
            top=200,
            fetch_all_pages=True,
            max_pages=20,
        )
    except Exception as e:
        plog.info(f"{_LOG_PREFIX} get_person_appointments failed error='{e}'")
        conv.log.error(
            "Cancel flow preload: get_person_appointments failed", error=str(e)
        )
        return LoadCancelAppointmentsResult(
            ok=False,
            utterance="We couldn't look up your appointments right now. Please try again later.",
        )

    plog.info(f"{_LOG_PREFIX} api_raw_appointment_count={len(raw)}")
    upcoming = filter_upcoming_active(raw)
    plog.info(f"{_LOG_PREFIX} after_filter_upcoming_active count={len(upcoming)}")

    hydrated: list[Appointment] = []
    for appt in upcoming:
        current = appt
        aid = current.appointment_id or current.id
        if not current.event_id and aid:
            full = handler.get_appointment(str(aid))
            if full is not None:
                plog.info(
                    f"{_LOG_PREFIX} hydrated event_id for appointment_id_last4="
                    f"'{str(aid)[-4:] if len(str(aid)) >= 4 else '****'}' "
                    f"had_event={bool(full.event_id)}"
                )
                current = full
        hydrated.append(current)

    dumped = [a.model_dump(mode="json") for a in hydrated]
    conv.state.cancel_upcoming_appointments = dumped
    conv.write_metric("CANCEL_FLOW_APPOINTMENTS_LOADED", len(hydrated))
    conv.log.info(
        "Cancel flow: loaded upcoming appointments (preload)",
        count=len(hydrated),
        person_id_last4=person_id[-4:] if len(person_id) >= 4 else "****",
    )
    sample_ids_last4: list[str] = []
    for row in dumped[:5]:
        if isinstance(row, dict):
            aid = row.get("appointmentId") or row.get("id") or ""
            sample_ids_last4.append(str(aid)[-4:] if aid else "")
    plog.info(
        f"{_LOG_PREFIX} stored cancel_upcoming_appointments count={len(dumped)}",
        sample_appointment_ids_last4=sample_ids_last4,
    )

    if not hydrated:
        plog.info(f"{_LOG_PREFIX} no hydrated appointments")
        return LoadCancelAppointmentsResult(
            ok=False,
            utterance=(
                "I don't see any upcoming appointments on your account in the next year. "
                "Is there something else I can help you with?"
            ),
        )

    plog.info(f"{_LOG_PREFIX} success hydrated_count={len(hydrated)}")
    return LoadCancelAppointmentsResult(ok=True, utterance="")


@func_description(
    "Preload upcoming appointments for cancel flow (used from IDNV and start_cancellation_flow)."
)
def load_cancel_upcoming_appointments(conv: Conversation) -> None:
    """Platform entry point for this module (helpers are imported directly)."""
    log_prefix = (
        "[load_cancel_upcoming_appointments.load_cancel_upcoming_appointments]: "
    )
    plog.info(f"{log_prefix} invoked")
