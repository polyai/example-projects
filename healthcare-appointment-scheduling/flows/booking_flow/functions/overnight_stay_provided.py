"""Called when caller answers admission question; sets appointment type."""

from datetime import date

import plog
from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


@func_description(
    "Called when the caller answers whether they were admitted to the hospital or stayed in the ER. Sets the final appointment type and routes to discharge date collection."
)
@func_parameter(
    "admitted_to_hospital",
    "True if the caller was admitted to the hospital (inpatient), False if they only stayed in the ER.",
)
def overnight_stay_provided(conv: Conversation, flow: Flow, admitted_to_hospital: bool):
    """Set appointment type from admission answer, then go to discharge date."""
    log_prefix = "[overnight_stay_provided]: "
    plog.info(f"{log_prefix} admitted_to_hospital={admitted_to_hospital}")

    if admitted_to_hospital:
        conv.state.booking_appointment_type = "hospital_follow_up"
        conv.state.booking_facility_type_label = "hospital"
    else:
        conv.state.booking_appointment_type = "er_follow_up"
        conv.state.booking_facility_type_label = "emergency room"

    plog.info(f"{log_prefix} booking_appointment_type='{conv.state.booking_appointment_type}'")

    conv.state.booking_today_date = date.today().isoformat()
    plog.info(f"{log_prefix} booking_today_date='{conv.state.booking_today_date}'")
    flow.goto_step("Collect Discharge Date")
    if conv.state.caller_is_case_manager:
        return {"utterance": "And when was the patient discharged?"}
    if admitted_to_hospital:
        if not conv.state.is_ooh:
            return {
                "utterance": (
                    "Got it, thank you. Just to let you know, since we'll be booking you in for a hospital follow up, "
                    "I'll need to transfer you to a transitional care nurse to go over your "
                    "plan of care after I put the appointment in our system. Could you tell me when you were discharged?"
                )
            }
        else:
            return handoff(
                conv,
                reason="HOSP_FU_OOH",
                utterance=(
                    "I'm sorry, but since this is a hospital follow up, which requires a transitional care nurse, and "
                    "it's out of hours for us, I'll need to transfer you to our voicemail. "
                    "Please leave a message, and someone will get back to you next business day."
                ),
            )

    return {"utterance": "And when were you discharged?"}
