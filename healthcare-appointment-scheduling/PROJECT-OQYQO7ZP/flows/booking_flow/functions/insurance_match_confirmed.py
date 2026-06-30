import plog
from _gen import *  # <AUTO GENERATED>
from functions.fetch_available_slots import filter_slots_for_extended_appointment
from functions.handoff import handoff
from functions.nextgen_response_models import AppointmentSlot
from functions.slot_matching import format_slot_offer_display, get_top_n_available_slots


def is_excluded_by_provider(conv, resource_id: str, plan_name: str) -> tuple[bool, str | None]:
    """Stub: no provider-level exclusions in the template."""
    return (False, None)


_LOG_PREFIX = "[insurance_match_confirmed]: "


@func_description("Called when the caller confirms the matched insurance plan is correct.")
def insurance_match_confirmed(conv: Conversation, flow: Flow) -> dict:
    matched = getattr(conv.state, "insurance_matched_plan_name", "")
    conv.state.insurance_verified_plan = matched
    conv.write_metric("INSURANCE_MATCH_CONFIRMED")
    plog.info(f"{_LOG_PREFIX} match confirmed: '{matched}'", is_pii=True)

    resource_id = getattr(conv.state, "patient_resource_id", None)
    if resource_id:
        excluded, provider_name = is_excluded_by_provider(conv, resource_id, matched)
        if excluded:
            plog.info(
                f"{_LOG_PREFIX} provider not credentialed: resource_id='{resource_id}' "
                f"plan='{matched}' provider='{provider_name}'",
                is_pii=True,
            )
            conv.write_metric("INSURANCE_PROVIDER_NOT_CREDENTIALED", matched)
            return handoff(
                conv,
                reason="INSURANCE_PROVIDER_NOT_CREDENTIALED",
                utterance=(
                    "Your insurance plan is accepted at Poly Clinic, but your current provider "
                    "isn't credentialed for it. Let me transfer you to our scheduling team who "
                    "can find the right provider for you. Putting you through now."
                ),
            )

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
    if existing_type:
        plog.info(
            f"{_LOG_PREFIX} appointment type already set: '{existing_type}'; "
            "skipping Collect Appointment Event Type"
        )
        from flows.booking_flow.functions.appointment_type_confirmed import (
            appointment_type_confirmed,
        )

        return appointment_type_confirmed(conv, flow, existing_type)

    flow.goto_step("Collect Appointment Event Type")
    return {"content": "Ask the caller what type of appointment they would like to book."}
