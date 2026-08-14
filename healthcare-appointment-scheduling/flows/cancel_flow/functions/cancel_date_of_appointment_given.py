from datetime import datetime

import plog

from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import (
    appointment_type_label,
    is_follow_up_appointment,
    resolve_cancel_appointments_from_date_parts,
)
from functions.handoff import handoff
from functions.nextgen_response_models import Appointment


def _readable_date(raw_dt: object) -> str:
    """'2026-03-28T00:00:00' → 'March 28, 2026'."""
    s = str(raw_dt).strip() if raw_dt else ""
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return (
                datetime.fromisoformat(s[:10]).strftime("%B %d, %Y").replace(" 0", " ")
            )
        except ValueError:
            pass
    return s or "an unknown date"


def _readable_time(raw_dt: object) -> str | None:
    """Extract a TTS-friendly time from an ISO datetime, or None if midnight / unparseable."""
    s = str(raw_dt).strip() if raw_dt else ""
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.hour == 0 and dt.minute == 0:
        return None
    hour = dt.hour
    minute = dt.minute
    if hour == 0:
        return f"12:{minute:02d} AM" if minute else "12 AM"
    if hour < 12:
        return f"{hour}:{minute:02d} AM" if minute else f"{hour} AM"
    if hour == 12:
        return f"12:{minute:02d} PM" if minute else "12 PM"
    h = hour - 12
    return f"{h}:{minute:02d} PM" if minute else f"{h} PM"


@func_description(
    "Record the appointment date the user wants to cancel as separate day, month, and year. Use N/A for missing parts when the year should be inferred from their loaded visits."
)
@func_parameter(
    "day_of_appointment_date",
    "The day of the appointment date as DD (01-31). Default to 'N/A' if not specified.",
)
@func_parameter(
    "month_of_appointment_date",
    "The month of the appointment date as MM (01-12). Default to 'N/A' if not specified.",
)
@func_parameter(
    "year_of_appointment_date",
    "The year of the appointment date as YYYY (4-digit). Use 'N/A' if the user only gave month and day and the year should be inferred from their upcoming visits.",
)
def cancel_date_of_appointment_given(
    conv: Conversation,
    flow: Flow,
    day_of_appointment_date: str,
    month_of_appointment_date: str,
    year_of_appointment_date: str,
):
    """Map structured date parts to a loaded appointment; follow-up only, else hand off."""
    log_prefix = "[cancel_date_of_appointment_given.cancel_date_of_appointment_given]: "
    raw = getattr(conv.state, "cancel_upcoming_appointments", None) or []
    appointments = [Appointment.model_validate(x) for x in raw]
    plog.info(
        f"{log_prefix} cancel_upcoming_appointments count={len(raw)} parsed_models={len(appointments)}"
    )

    matches, parse_err = resolve_cancel_appointments_from_date_parts(
        appointments,
        str(day_of_appointment_date),
        str(month_of_appointment_date),
        str(year_of_appointment_date),
    )

    if parse_err == "missing_day_or_month":
        plog.info(f"{log_prefix} parse_err=missing_day_or_month")
        return {"utterance": ("What date is the visit you're trying to cancel?")}

    if parse_err == "invalid_components":
        plog.info(f"{log_prefix} parse_err=invalid_components")
        return {
            "utterance": (
                "I didn't quite get that date—could you tell me the month and day again?"
            )
        }

    conv.write_metric("CANCEL_DATE_PARTS_RECORDED", True)
    plog.info(f"{log_prefix} match_count={len(matches)}")

    if len(matches) == 0:
        plog.info(f"{log_prefix} zero matches; staying on Resolve Appointment")
        flow.goto_step(
            "Resolve Appointment",
            "No appointment on that date; ask for a different date.",
        )
        return {
            "utterance": (
                "I don't see an upcoming visit on that date. Which visit would you like to cancel?"
            )
        }

    if len(matches) > 1:
        plog.info(
            f"{log_prefix} ambiguous date; match_count={len(matches)}",
            appointment_ids_last4=[
                str(m.appointment_id or m.id or "")[-4:] for m in matches[:10]
            ],
        )
        conv.write_metric("CANCEL_FLOW_AMBIGUOUS_DATE", len(matches))

        # Try to build disambiguation labels — first by type, then by time
        type_labels = [appointment_type_label(m.event_id) for m in matches]
        unique_types = set(type_labels)
        can_disambiguate_by_type = (
            len(unique_types) > 1 and "appointment" not in unique_types
        )

        if can_disambiguate_by_type:
            labels = [f"the {lbl}" for lbl in type_labels]
        else:
            # Try time-based disambiguation using already-loaded appointment data
            plog.info(
                f"{log_prefix} type labels insufficient ({type_labels}); trying time-based"
            )
            times: list[str | None] = [
                _readable_time(m.appointment_date) for m in matches
            ]

            non_none_times = [t for t in times if t is not None]
            can_disambiguate_by_time = len(non_none_times) == len(matches) and len(
                set(non_none_times)
            ) == len(matches)

            if can_disambiguate_by_time:
                labels = [f"the {t} appointment" for t in times]
            else:
                plog.info(f"{log_prefix} cannot disambiguate; handing off")
                return handoff(
                    conv,
                    reason="CANCEL_AMBIGUOUS_DATE",
                    utterance="We found more than one visit on that day. I’ll transfer you to a team member who can cancel the right one.",
                )

        # Store matches for the disambiguation step
        conv.state.cancel_ambiguous_matches = [
            m.model_dump(mode="json") for m in matches
        ]
        when = _readable_date(matches[0].appointment_date)
        options = " or ".join(labels)
        plog.info(f"{log_prefix} disambiguating: {options}", is_pii=True)
        flow.goto_step("Disambiguate Appointment")
        return {
            "utterance": (
                f"I see you have more than one visit on {when}. "
                f"Which one would you like to cancel — {options}?"
            )
        }

    chosen = matches[0]
    chosen_id = chosen.appointment_id or chosen.id
    day_iso = (
        str(chosen.appointment_date)[:10]
        if chosen.appointment_date and len(str(chosen.appointment_date)) >= 10
        else "unknown"
    )
    plog.info(
        f"{log_prefix} single_match appointment_id_last4="
        f"'{str(chosen_id)[-4:] if chosen_id and len(str(chosen_id)) >= 4 else '****'}' "
        f"event_id='{chosen.event_id}' is_follow_up={is_follow_up_appointment(chosen)} "
        f"day='{day_iso}'",
        is_pii=True,
    )

    if not is_follow_up_appointment(chosen):
        conv.write_metric("CANCEL_FLOW_NON_FOLLOW_UP", True)
        conv.write_metric("CANCEL_OOS", True)
        return handoff(
            conv,
            reason="CANCEL_NON_FOLLOW_UP",
            utterance="That type of visit can’t be cancelled on this line. I’ll transfer you to someone who can help.",
        )

    if chosen.is_rescheduled is True:
        plog.info(f"{log_prefix} appointment already rescheduled; exiting flow")
        conv.write_metric("CANCEL_FLOW_ALREADY_RESCHEDULED", True)
        conv.state.pending_transfer_reason = "CANCEL_ALREADY_RESCHEDULED"
        conv.exit_flow()
        return {
            "content": (
                "This appointment has already been rescheduled, so it can’t be cancelled "
                "through this line. Offer to transfer the caller to someone who can help, "
                "but first ask if there’s anything else they need."
            )
        }

    appt_id = chosen.appointment_id or chosen.id
    if not appt_id:
        plog.info(f"{log_prefix} matched appointment missing id; exiting")
        conv.log.error("Cancel flow: matched appointment has no id")
        conv.exit_flow()
        return {
            "utterance": "Something went wrong matching that appointment. Please try again.",
        }

    conv.state.cancel_target_appointment_id = str(appt_id)
    plog.info(
        f"{log_prefix} set cancel_target_appointment_id_last4="
        f"'{str(appt_id)[-4:] if len(str(appt_id)) >= 4 else '****'}'"
    )
    conv.log.info(
        "Cancel flow: matched follow-up appointment",
        appointment_id_last4=str(appt_id)[-4:] if len(str(appt_id)) >= 4 else "****",
    )

    flow.goto_step("Confirm Cancellation")
    when = _readable_date(chosen.appointment_date or day_iso)
    plog.info(
        f"{log_prefix} goto_step='Confirm Cancellation' when='{when}'", is_pii=True
    )
    return {
        "utterance": (
            f"We can cancel that follow-up visit on {when}. "
            "Do you want to go ahead and cancel that?"
        )
    }
