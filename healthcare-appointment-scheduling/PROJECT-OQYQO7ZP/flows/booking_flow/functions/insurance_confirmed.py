import plog
from _gen import *  # <AUTO GENERATED>
from functions.fetch_available_slots import filter_slots_for_extended_appointment
from functions.handoff import handoff
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import format_slot_offer_display, get_top_n_available_slots


def is_not_accepted(plan_name: str) -> tuple[bool, str | None]:
    """Stub: all insurance plans are accepted in the template."""
    return (False, None)


def is_excluded_by_provider(conv, resource_id: str, plan_name: str) -> tuple[bool, str | None]:
    """Stub: no provider-level exclusions in the template."""
    return (False, None)


_LOG_PREFIX = "[insurance_confirmed]: "


@func_description(
    "Called when the caller confirms their insurance on file is still current. Checks if the plan is accepted by Poly Clinic."
)
def insurance_confirmed(conv: Conversation, flow: Flow) -> dict:
    payer_name = getattr(conv.state, "insurance_on_file_payer_name", "") or ""
    conv.state.insurance_verified_plan = payer_name
    conv.write_metric("INSURANCE_CONFIRMED_ON_FILE")

    rejected, matched_name = is_not_accepted(payer_name)
    if rejected:
        plog.info(f"{_LOG_PREFIX} plan not accepted: '{matched_name}'", is_pii=True)
        conv.write_metric("INSURANCE_NOT_ACCEPTED", matched_name)
        return handoff(
            conv,
            reason="INSURANCE_NOT_ACCEPTED",
            utterance=(
                "Unfortunately, we're not currently accepting that insurance plan for scheduling. "
                "Let me transfer you to our patient accounts team who can assist you further. "
                "Putting you through now."
            ),
        )

    resource_id = getattr(conv.state, "patient_resource_id", None)
    if resource_id:
        excluded, provider_name = is_excluded_by_provider(conv, resource_id, payer_name)
        if excluded:
            plog.info(
                f"{_LOG_PREFIX} provider not credentialed: resource_id='{resource_id}' "
                f"plan='{payer_name}' provider='{provider_name}'",
                is_pii=True,
            )
            conv.write_metric("INSURANCE_PROVIDER_NOT_CREDENTIALED", payer_name)
            return handoff(
                conv,
                reason="INSURANCE_PROVIDER_NOT_CREDENTIALED",
                utterance=(
                    "Your insurance plan is accepted at Poly Clinic, but your current provider "
                    "isn't credentialed for it. Let me transfer you to our scheduling team who "
                    "can find the right provider for you. Putting you through now."
                ),
            )

    plog.info(f"{_LOG_PREFIX} plan accepted: '{payer_name}'", is_pii=True)
    conv.write_metric("INSURANCE_ACCEPTED")

    if getattr(conv.state, "booking_slots_prefetched", False):
        if getattr(conv.state, "patient_needs_extended_appointment", False):
            raw_slots = getattr(conv.state, "booking_available_slots", None) or []
            all_slots = [AppointmentSlot.model_validate(s) for s in raw_slots]
            filtered = filter_slots_for_extended_appointment(all_slots)
            if not filtered:
                plog.info(f"{_LOG_PREFIX} no :00/:45 slots for extended appointment; handing off")
                return handoff(
                    conv,
                    reason="BOOKING_NO_EXTENDED_SLOTS",
                    utterance=(
                        "I'm not finding any available appointment times that fit the extended "
                        "scheduling requirement. Let me transfer you to someone who can help."
                    ),
                )
            offered = get_top_n_available_slots(filtered, n=2)
            conv.state.booking_offered_slot_1 = offered[0].model_dump(mode="json")
            conv.state.booking_offered_slot_2 = (
                offered[1].model_dump(mode="json") if len(offered) > 1 else None
            )
            conv.state.booking_offered_slot_3 = None
            slots_display = format_slot_offer_display(offered)
            conv.state.booking_offered_slots_display = slots_display
            plog.info(f"{_LOG_PREFIX} extended filter applied; re-selected {len(offered)} slot(s)")

        slots_display = getattr(conv.state, "booking_offered_slots_display", "")
        nbr = getattr(conv.state, "booking_neighborhood_fallback", False)
        no_pref = getattr(conv.state, "booking_no_pref_match_on_prefetch", False)
        requested_today = getattr(conv.state, "booking_requested_today_on_prefetch", False)
        nbr_part = (
            "Your primary provider doesn't have any openings right now, but I do have "
            "some times available with another provider on your care team. "
            if nbr
            else ""
        )
        if requested_today and getattr(conv.state, "booking_appointment_type", None) == "ill":
            from datetime import UTC
            from datetime import datetime as _dt

            _today_iso = _dt.now(UTC).strftime("%Y-%m-%d")
            _s1 = getattr(conv.state, "booking_offered_slot_1", None) or {}
            _s2 = getattr(conv.state, "booking_offered_slot_2", None) or {}
            _has_today = any(
                str(s.get("start_date", "")).startswith(_today_iso) for s in [_s1, _s2] if s
            )
            if not _has_today:
                plog.info(
                    f"{_LOG_PREFIX} ill visit requested today but no today slots (prefetch); confirming need"
                )
                flow.goto_step("Confirm Same Day Need")
                return {
                    "utterance": (
                        "I'm not seeing any openings for today. Do you need to be seen today "
                        "specifically, or would another day work as well?"
                    )
                }
        if no_pref and requested_today:
            offer = f"{nbr_part}I wasn't able to find any appointments for today, but the next available times I'm seeing are {slots_display}. Would one of those work for you?"
        elif no_pref:
            offer = f"{nbr_part}I wasn't able to find anything at that time, but I'm seeing {slots_display}. Would one of those work for you?"
        else:
            offer = f"{nbr_part}I'm seeing {slots_display}. Would one of those work for you?"
        plog.info(f"{_LOG_PREFIX} slots pre-fetched; goto_step='Offer Booking Slot'")
        flow.goto_step("Offer Booking Slot")
        return {"utterance": offer}

    existing_type = getattr(conv.state, "booking_appointment_type", None)
    needs_extended = getattr(conv.state, "patient_needs_extended_appointment", False)
    if existing_type and not needs_extended:
        plog.info(
            f"{_LOG_PREFIX} appointment type already set: '{existing_type}'; "
            "skipping Collect Appointment Event Type"
        )
        from flows.booking_flow.functions.appointment_type_confirmed import (
            appointment_type_confirmed,
        )

        return appointment_type_confirmed(conv, flow, existing_type)

    if needs_extended and existing_type:
        plog.info(
            f"{_LOG_PREFIX} extended appointment patient — clearing pre-detected type "
            f"'{existing_type}' to ask caller directly"
        )
        conv.state.booking_appointment_type = None

    flow.goto_step("Collect Appointment Event Type")
    return {"content": "Ask the caller what type of appointment they would like to book."}
