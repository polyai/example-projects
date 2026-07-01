from datetime import datetime

from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff
from functions.routes_api_call import get_service_types, search_appointments_by_customer
from functions.utils import (
    get_most_recent_date,
    get_prompt_for_appointment_timeframe_readback,
    is_more_than_months_ago,
    is_within_days,
)


@func_description("retrieve the user's appointments")
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=4,
    delay_responses=[("just a moment please", 3)],
)
def retrieve_appointments(conv: Conversation, flow: Flow):
    try:
        all_appointments = search_appointments_by_customer(conv)
        pending_appointments = [
            appointment
            for appointment in all_appointments
            if appointment["statusText"] not in ["Cancelled", "Completed"]
        ]
        completed_appointment_dates = [
            appt["date"] for appt in all_appointments if appt["statusText"] == "Completed"
        ]
        conv.state.service_type_ids = ",".join(
            [appointment["type"] for appointment in pending_appointments]
        )
    except Exception:
        conv.log.error("error while getting appointments", exc_info=True)
        handoff_reason = "API_TIMEOUT" if conv.state.api_timeout else "API_ERROR"
        return handoff(
            conv,
            handoff_reason,
            "I'm afraid I am facing some technical difficulties at this moment, let me put you through to someone who can help, just a moment please!",
            "CUSTOMER_CARE",
        )

    try:
        service_types = get_service_types(conv)
    except Exception:
        conv.log.error("error while getting service types", exc_info=True)
        handoff_reason = "API_TIMEOUT" if conv.state.api_timeout else "API_ERROR"
        return handoff(
            conv,
            handoff_reason,
            "I'm afraid I am facing some technical difficulties at this moment, let me put you through to someone who can help, just a moment please!",
            "CUSTOMER_CARE",
        )

    for appointment in pending_appointments:
        appointment["serviceType"] = next(
            s for s in service_types if s["typeID"] == appointment["type"]
        )
        appointment["dayOfWeek"] = datetime.strptime(appointment["date"], "%Y-%m-%d").strftime("%A")
        appointment["endToSay"] = (
            "sunset" if appointment["end"] == "20:00:00" else appointment["end"]
        )

    conv.state.appointments = pending_appointments

    appointment_dates = []
    for appointment in pending_appointments:
        if appointment["date"] not in appointment_dates:
            appointment_dates.append(appointment["date"])
    conv.state.appointment_dates = appointment_dates

    if len(pending_appointments) == 1:
        appointment = pending_appointments[0]
        conv.state.appointment = appointment
        appointment_timeframe_readback_prompt = get_prompt_for_appointment_timeframe_readback(
            appointment, conv.state.call_intent
        )
        flow.goto_step("Confirm appointment")
        return f"""You have found the user's appointment. Say: "So I see a service appointment here for {appointment["date"]} {appointment_timeframe_readback_prompt}"
        """
    elif len(pending_appointments) > 1:
        if conv.state.call_intent == "schedule":
            return handoff(
                conv,
                "CUSTOMER_WANTS_NEW_APPOINTMENT_BUT_ALREADY_HAS_SEVERAL",
                "Thank you. Let me put you through to a colleague who can help you with this, just a moment please!",
                "CUSTOMER_CARE",
            )
        if len(appointment_dates) == 1:
            flow.goto_step("Several appointments on same day")
            conv.state.appointment_date = appointment_dates[0]
            conv.state.appointments_on_date = pending_appointments
            return "You have found several upcoming appointments on the same day."
        flow.goto_step("Several appointments on different days")
        return "You have found several upcoming appointments."
    else:
        if conv.state.call_intent == "schedule":
            last_completed = get_most_recent_date(completed_appointment_dates)
            if not last_completed:
                return handoff(
                    conv,
                    "CUSTOMER_WANTS_INITIAL_APPOINTMENT",
                    "Thank you. Let me put you through to a colleague who can help you with this, just a moment please!",
                    "CUSTOMER_CARE",
                )

            if is_within_days(conv.state.current_date_ymd, last_completed, 10):
                flow.goto_step("Await response to days suggestion")
                # utterance needs to be hardcoded, otherwise can trigger goodbye stop keyword from verbiage around calling back later
                return {
                    "utterance": "I see that your treatment was done quite recently. To get the best results, we'll need to wait 7 to 10 days before doing another treatment for the same issue. Do you mind calling us back after that?",
                }

            if is_more_than_months_ago(last_completed, conv.state.current_date_ymd, 5):
                return handoff(
                    conv,
                    "NO_SERVICE_WITHIN_5_MONTHS",
                    "I need to connect you with one of our customer care team members who can best assist you with scheduling. One moment please.",
                    "CUSTOMER_CARE",
                )

            conv.write_metric("MAKE_APPOINTMENT_FLOW_INITIATED", None)
            conv.goto_flow("schedule_appointment")
            return f"""Let the user know that their last service was about [time in weeks (or months) between their last service {last_completed} and now], and that you can schedule in a new appointment for them."""
        return handoff(
            conv,
            "NO_ACTIVE_APPOINTMENTS",
            "I'm not seeing an active appointment, let me transfer you to a colleague who can help with this. One moment please.",
            "CUSTOMER_CARE",
        )
