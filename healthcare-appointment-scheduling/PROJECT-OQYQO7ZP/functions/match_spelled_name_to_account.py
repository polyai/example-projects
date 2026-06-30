import plog
from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import get_recall_window, is_recheck_type
from functions.extract_time_preference import extract_time_preference_from_conversation
from functions.fetch_available_slots import FPIM_SD_CATEGORY_ID, fetch_booking_slots_for_state
from functions.get_grace_nextgen_api_handler import get_grace_nextgen_api_handler
from functions.handoff import handoff
from functions.load_cancel_upcoming_appointments import (
    load_cancel_upcoming_appointments_for_state,
)
from functions.load_reschedule_upcoming_appointments import (
    load_reschedule_upcoming_appointments_for_state,
)
from functions.nextgen_response_models import Appointment, AppointmentSlot
from functions.slot_matching import (
    format_slot_offer_display,
    get_top_n_available_slots,
    get_top_n_preference_slots,
)


def get_resource_id_for_provider(conv, pcp_id: str) -> str | None:
    """In the mock, provider ID == resource ID."""
    return pcp_id


_POST_IDNV_CANCEL_FLOW = "Cancel Flow"
_POST_IDNV_RESCHEDULE_FLOW = "Reschedule Flow"
_POST_IDNV_BOOKING_FLOW = "Booking Flow"

_PREFETCHABLE_BOOKING_TYPES = {
    "recheck",
    "recheck_diabetes",
    "recheck_hypertension",
    "recheck_medication",
    "ill",
}

_ENGLISH_LANGUAGE_ID = "A38610EE-37FF-42E1-93B0-E563D7144DC2"


def _coalesce_str_id(value) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _patient_language_barrier_from_fields(
    language_id,
    uds_language_barrier_id,
) -> bool:
    lang_norm = (_coalesce_str_id(language_id) or "").upper()
    uds_raw = _coalesce_str_id(uds_language_barrier_id)
    if lang_norm and lang_norm != _ENGLISH_LANGUAGE_ID.upper():
        return True
    if not lang_norm and uds_raw:
        return True
    return False


def _language_fields_from_identified_patient(patient) -> tuple[str | None, str | None]:
    if not isinstance(patient, dict):
        return None, None
    lid = (
        patient.get("preferredLanguageId")
        or patient.get("languageId")
        or patient.get("language_id")
    )
    uds = patient.get("udsLanguageBarrierId") or patient.get("uds_language_barrier_id")
    return _coalesce_str_id(lid), _coalesce_str_id(uds)


def _identity_verified_prefix(conv) -> str:
    if getattr(conv.state, "caller_is_case_manager", False):
        return "Alright, thanks for verifying the patient's identity. "
    return "Alright, thanks for verifying your identity. "


def _we_verified_prefix(conv) -> str:
    if getattr(conv.state, "caller_is_case_manager", False):
        return "We've verified the patient's identity. "
    return "We've verified your identity. "


def account_display_name(patient) -> str:
    if isinstance(patient, dict):
        first = (patient.get("first_name") or patient.get("firstName") or "").strip()
        last = (patient.get("last_name") or patient.get("lastName") or "").strip()
    else:
        first = (
            getattr(patient, "first_name", None) or getattr(patient, "firstName", None) or ""
        ).strip()
        last = (
            getattr(patient, "last_name", None) or getattr(patient, "lastName", None) or ""
        ).strip()
    return f"{first} {last}".strip() or "Unknown"


def _prefetch_booking_slots_utterance(conv, pre_event_type: str) -> str:
    log_prefix = "[match_spelled_name_to_account._prefetch_booking_slots_utterance]: "
    fallback = {
        "content": "The caller's identity has been verified. Proceed with the booking flow."
    }

    identified = getattr(conv.state, "identified_patient", None)
    cell_phone = identified.get("cellPhone") if isinstance(identified, dict) else None
    if not cell_phone:
        plog.info(f"{log_prefix} no cellPhone on record; skipping pre-fetch")
        return fallback

    start_override = None
    end_override = None
    if is_recheck_type(pre_event_type):
        recall = get_recall_window(conv, pre_event_type)
        if recall.needs_disambiguation:
            conv.state.booking_recheck_disambiguation = recall.disambiguation_options
            plog.info(f"{log_prefix} recheck disambiguation needed; skipping prefetch")
            return fallback
        if not recall.ok:
            plog.info(f"{log_prefix} no recall for '{pre_event_type}'; deferring to booking flow")
            return fallback
        if recall.resolved_appointment_type:
            pre_event_type = recall.resolved_appointment_type
            plog.info(f"{log_prefix} refined pre_event_type to '{pre_event_type}' from recall")
        start_override = recall.start_iso
        end_override = recall.end_iso
        conv.state.booking_recall_expected_return_date = recall.expected_return_date

    conv.state.booking_appointment_type = pre_event_type
    conv.write_metric("BOOKING_FLOW_TYPE_CONFIRMED", pre_event_type)

    if pre_event_type == "ill":
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        today_start = now.strftime("%Y-%m-%dT00:00:00")
        today_end = now.strftime("%Y-%m-%dT23:59:59")
        plog.info(f"{log_prefix} ill visit: trying FP/IM SD same-day slots first")
        try:
            sd_result = fetch_booking_slots_for_state(
                conv,
                start_override=today_start,
                end_override=today_end,
                category_id_override=FPIM_SD_CATEGORY_ID,
                skip_blocked_dates=True,
            )
            sd_slots = getattr(conv.state, "booking_available_slots", None) or []
            if sd_result.ok and sd_slots:
                plog.info(
                    f"{log_prefix} ill visit: found {len(sd_slots)} FP/IM SD same-day slot(s)"
                )
                conv.state.booking_used_same_day_category = True
            else:
                plog.info(
                    f"{log_prefix} ill visit: no FP/IM SD same-day slots; falling back to FP/IM"
                )
        except Exception as exc:
            plog.info(f"{log_prefix} ill visit: FP/IM SD fetch failed error='{exc}'")

    already_fetched = pre_event_type == "ill" and getattr(
        conv.state, "booking_used_same_day_category", False
    )
    if not already_fetched:
        try:
            fetch_result = fetch_booking_slots_for_state(
                conv, start_override=start_override, end_override=end_override
            )
        except Exception as exc:
            plog.info(f"{log_prefix} fetch raised error='{exc}'; using fallback")
            return fallback

        if not fetch_result.ok:
            plog.info(f"{log_prefix} fetch not ok; using fallback")
            return fallback

    raw_slots = getattr(conv.state, "booking_available_slots", None) or []
    all_slots = [AppointmentSlot.model_validate(s) for s in raw_slots]

    pref = extract_time_preference_from_conversation(conv)
    plog.info(
        f"{log_prefix} pref.has_preference={pref.has_preference} "
        f"date='{pref.requested_date}' time='{pref.requested_time}'",
        is_pii=True,
    )

    offered: list[AppointmentSlot] = []
    no_pref_match = False
    if pref.has_preference:
        offered = get_top_n_preference_slots(
            requested_date=pref.requested_date,
            requested_time=pref.requested_time,
            slots=all_slots,
            n=2,
        )
        if not offered:
            no_pref_match = True
            offered = get_top_n_available_slots(all_slots, n=2)
            conv.state.booking_no_pref_match_confirmed = True
    else:
        offered = get_top_n_available_slots(all_slots, n=2)

    if not offered:
        plog.info(f"{log_prefix} no slots after filtering; using fallback")
        return fallback

    conv.state.booking_offered_slot_1 = offered[0].model_dump(mode="json")
    conv.state.booking_offered_slot_2 = (
        offered[1].model_dump(mode="json") if len(offered) > 1 else None
    )
    conv.state.booking_offered_slot_3 = None
    slots_display = format_slot_offer_display(offered)
    conv.state.booking_offered_slots_display = slots_display
    conv.write_metric("BOOKING_FLOW_SLOTS_OFFERED")
    conv.state.booking_slots_prefetched = True

    plog.info(f"{log_prefix} pre-fetched; display='{slots_display[:80]}'", is_pii=True)

    conv.state.booking_no_pref_match_on_prefetch = no_pref_match

    from datetime import UTC
    from datetime import datetime as _dt

    _today_iso = _dt.now(UTC).strftime("%Y-%m-%d")
    _rd = (pref.requested_date or "").strip().lower()
    conv.state.booking_requested_today_on_prefetch = (
        pref.has_preference and bool(_rd) and (_rd == "today" or _rd.startswith(_today_iso))
    )

    return {"content": "The caller's identity has been verified. Proceed with the booking flow."}


def _resolve_pcp_and_language(conv, log_prefix: str):
    patient = getattr(conv.state, "identified_patient", None) or {}
    person_id = patient.get("id") if isinstance(patient, dict) else None

    if person_id:
        identified_dict = patient if isinstance(patient, dict) else {}
        try:
            handler = get_grace_nextgen_api_handler(conv)
            full_person = handler.get_person(person_id)
            pcp_id = full_person.primary_care_provider_id if full_person else None
            conv.state.patient_primary_care_provider_id = pcp_id
            language_id = full_person.language_id if full_person else None
            uds_barrier_id = full_person.uds_language_barrier_id if full_person else None
            plog.info(
                f"{log_prefix} get_person language diagnostic "
                f"full_person_present={bool(full_person)} "
                f"language_id={language_id!r} uds_language_barrier_id={uds_barrier_id!r}",
                is_pii=True,
            )
            conv.state.patient_language_barrier = _patient_language_barrier_from_fields(
                language_id, uds_barrier_id
            )
            if conv.state.patient_language_barrier:
                plog.info(f"{log_prefix} language barrier detected; 30-min slots required")
            if pcp_id:
                resource_id = get_resource_id_for_provider(conv, pcp_id)
                conv.state.patient_resource_id = resource_id
                plog.info(
                    f"{log_prefix} pcp_id='{pcp_id}' resource_id='{resource_id}'", is_pii=True
                )
                if not resource_id:
                    return handoff(
                        conv,
                        reason="PATIENT_PROVIDER_NOT_RECOGNIZED",
                        utterance="I'll need to transfer you to someone who can help with this. Putting you through now.",
                    )
            else:
                conv.state.patient_resource_id = None
                conv.log.warning(
                    f"{log_prefix} GET /persons returned no primaryCareProviderId",
                    person_id=person_id,
                    is_pii=True,
                )
        except Exception as exc:
            conv.log.error(f"{log_prefix} failed to fetch person for PCP lookup", error=str(exc))
            conv.state.patient_primary_care_provider_id = None
            conv.state.patient_resource_id = None
            fb_lang, fb_uds = _language_fields_from_identified_patient(identified_dict)
            conv.state.patient_language_barrier = _patient_language_barrier_from_fields(
                fb_lang, fb_uds
            )
            conv.log.warning(
                f"{log_prefix} get_person failed; using identified_patient for language_barrier",
                error=str(exc),
                fallback_language_id=fb_lang,
                fallback_uds_language_barrier_id=fb_uds,
                patient_language_barrier=conv.state.patient_language_barrier,
                is_pii=True,
            )
    else:
        plog.info(f"{log_prefix} no person_id on identified_patient; skipping PCP lookup")
        conv.state.patient_primary_care_provider_id = None
        conv.state.patient_resource_id = None
        fb_lang, fb_uds = _language_fields_from_identified_patient(
            patient if isinstance(patient, dict) else {}
        )
        conv.state.patient_language_barrier = _patient_language_barrier_from_fields(fb_lang, fb_uds)
        conv.log.warning(
            f"{log_prefix} no person_id; PCP skipped; language from lookup payload",
            fallback_language_id=fb_lang,
            fallback_uds_language_barrier_id=fb_uds,
            patient_language_barrier=conv.state.patient_language_barrier,
            is_pii=True,
        )
    return None


def _format_cancel_appointments(conv) -> str:
    from functions.appointment_selection import is_follow_up_appointment

    raw = getattr(conv.state, "cancel_upcoming_appointments", None) or []
    appts = [Appointment.model_validate(x) for x in raw] if raw else []
    eligible = [
        a
        for a in appts
        if is_follow_up_appointment(a) and a.appointment_date and a.is_rescheduled is not True
    ]
    eligible.sort(key=lambda a: str(a.appointment_date))
    if not eligible:
        return ""
    from datetime import datetime as _dt

    def _fmt(raw_dt: str) -> str:
        s = str(raw_dt).strip()
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            try:
                return _dt.fromisoformat(s[:10]).strftime("%B %d, %Y").replace(" 0", " ")
            except ValueError:
                pass
        return s

    if len(eligible) == 1:
        return f"I can see you have a visit on {_fmt(eligible[0].appointment_date)}. "
    dates = ", ".join(_fmt(a.appointment_date) for a in eligible)
    return f"I can see you have visits on {dates}. "


def _build_pending_flow_utterance(conv, pending: str, log_prefix: str) -> str | dict:
    if pending == _POST_IDNV_RESCHEDULE_FLOW:
        prefix = _we_verified_prefix(conv)
        if getattr(conv.state, "caller_is_case_manager", False):
            return (
                prefix + "We have their upcoming visits on file. "
                "Which appointment would you like to reschedule?"
            )
        return (
            prefix + "We have your upcoming visits on file. "
            "Which appointment would you like to reschedule?"
        )

    if pending == _POST_IDNV_CANCEL_FLOW:
        prefix = _we_verified_prefix(conv)
        appt_list = _format_cancel_appointments(conv)
        if getattr(conv.state, "caller_is_case_manager", False):
            return prefix + appt_list + "Which appointment would you like to cancel?"
        return prefix + appt_list + "Which appointment would you like to cancel?"

    if pending == _POST_IDNV_BOOKING_FLOW:
        pre_idnv_event_type = getattr(conv.state, "booking_pre_idnv_event_type", None)
        prefix = _identity_verified_prefix(conv)
        is_cm = getattr(conv.state, "caller_is_case_manager", False)
        if pre_idnv_event_type in _PREFETCHABLE_BOOKING_TYPES:
            prefetch_result = _prefetch_booking_slots_utterance(conv, pre_idnv_event_type)
            if isinstance(prefetch_result, dict):
                return prefetch_result
            return prefetch_result
        if pre_idnv_event_type:
            return {
                "content": "The caller's identity has been verified. Proceed with the booking flow."
            }
        if is_cm:
            return (
                prefix + "Is this appointment for a follow-up on something"
                " they've seen their provider for before, or for a new issue?"
            )
        return (
            prefix + "Is this appointment for a follow-up on something"
            " you've seen your provider for before, or for a new issue?"
        )

    return _we_verified_prefix(conv) + "Your account is now identified for this call. Continuing."


def handle_name_matched(conv, log_prefix: str):
    """Shared post-match logic for both spoken and spelled name verification."""
    conv.write_metric("IDNV_FLOW_NAME_COLLECTED")
    conv.write_metric("IDNV_FLOW_COMPLETED")
    conv.write_metric("IDNV_IDENTIFIED")

    handoff_result = _resolve_pcp_and_language(conv, log_prefix)
    if handoff_result is not None:
        return handoff_result

    pending = getattr(conv.state, "post_idnv_flow_name", None)
    plog.info(f"{log_prefix} name matched; post_idnv_flow_name='{pending}'")

    if pending:
        conv.state.post_idnv_flow_name = None
        if pending == _POST_IDNV_CANCEL_FLOW:
            preload = load_cancel_upcoming_appointments_for_state(conv)
            if not preload.ok:
                plog.info(f"{log_prefix} cancel preload failed")
                conv.exit_flow()
                return {"utterance": preload.utterance}
        elif pending == _POST_IDNV_RESCHEDULE_FLOW:
            preload = load_reschedule_upcoming_appointments_for_state(conv)
            if not preload.ok:
                plog.info(f"{log_prefix} reschedule preload failed")
                conv.exit_flow()
                return {"utterance": preload.utterance}
        conv.goto_flow(pending)
        utterance = _build_pending_flow_utterance(conv, pending, log_prefix)
        if isinstance(utterance, dict):
            return utterance
        return {"utterance": utterance}

    conv.exit_flow()
    return {
        "content": (
            "Tell the user you've confirmed their account and ask how you can help them today."
        )
    }


@func_description("Called when the caller has spelled their name for verification.")
def match_spelled_name_to_account(conv: Conversation):
    log_prefix = "[match_spelled_name_to_account]: "
    patient = getattr(conv.state, "identified_patient", None)
    if not patient:
        return handoff(
            conv,
            reason="IDNV_NAME_MATCH_NO_ACCOUNT",
            utterance="Please hold while I transfer you to someone who can help.",
        )

    account_name = account_display_name(patient)

    candidates = getattr(conv.state, "idnv_candidate_patients", None) or []
    single_dob_match = len(candidates) <= 1

    prompt = (
        "You are a name matcher for identity verification. The caller's FIRST "
        "spoken name did not match, so they were asked to spell or repeat their "
        "name. You must now evaluate ONLY the caller's SECOND attempt — the "
        "response given AFTER the agent asked them to spell their name.\n\n"
        "IMPORTANT: Completely IGNORE the first name the caller gave earlier in "
        "the conversation. It was wrong or misheard. Only use the caller's most "
        "recent response (after the spelling request) to determine the name.\n\n"
    )

    if single_dob_match:
        prompt += (
            "IMPORTANT CONTEXT: The caller's phone number and date of birth "
            "have ALREADY been verified and uniquely match this account. "
            "Identity is strongly established. Be very generous — a match on "
            "first name OR last name alone is sufficient. Only return no_match "
            "if the stated name is clearly a completely different person.\n\n"
        )

    prompt += (
        "The caller may have:\n"
        "- Spelled letters out loud (e.g. 'J-O-H-N' or 'Jay, Ay, Ess, Oh, En')\n"
        "- Said the name normally instead of spelling it\n"
        "- Given a mix of spelling and speaking\n\n"
        "ASR often transcribes individual letters as words or similar-sounding "
        "words. Reconstruct the intended name generously.\n\n"
        "Match criteria (be lenient — this is a second chance):\n"
        "1. If the reconstructed first AND last name are clearly the same person "
        "as the account, return match.\n"
        "2. Allow ASR errors in individual letters (e.g. 'B'/'D', 'M'/'N', "
        "'S'/'F'), homophones ('Down'/'Dunn'), nicknames ('Jon'/'John', "
        "'Mike'/'Michael'), and minor spelling differences.\n"
        "3. Only return no_match if the names clearly refer to a different "
        "person.\n\n"
        f"Account name on file:\n{account_name!r}\n\n"
        f"Transcript alternatives (from ASR): \n{conv.transcript_alternatives}\n\n"
        "OUTPUT FORMAT:\n"
        "Return ONLY one word: match or no_match"
    )

    try:
        result = conv.utils.prompt_llm(prompt, show_history=True)
    except Exception as e:
        conv.log.error("match_spelled_name_to_account prompt_llm failed", error=str(e))
        return handoff(
            conv,
            reason="IDNV_NAME_MATCH_ERROR",
            utterance="Let me put you through to someone who can help you with this.",
        )

    raw = (result or "").strip().lower()
    is_match = raw == "match"
    conv.log.info(
        "IDNV spelled name match result",
        account_name=account_name,
        is_match=is_match,
        llm_response=(result or "").strip()[:50],
        is_pii=True,
    )

    if not is_match:
        return handoff(
            conv,
            reason="IDNV_NAME_NO_MATCH",
            utterance=(
                "I still wasn't able to match that to the account. "
                "Let me transfer you to someone who can help."
            ),
        )

    return handle_name_matched(conv, log_prefix)
