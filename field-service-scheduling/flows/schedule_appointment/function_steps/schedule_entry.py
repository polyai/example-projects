from _gen import *  # <AUTO GENERATED>
from flows.schedule_appointment.functions.update_visit_request import request_state
from functions import idnv, visits


def schedule_entry(conv: Conversation, flow: Flow):
    """Entry gate: unverified callers go to verify_caller and come back here."""
    conv.state.task = "schedule"
    gate = idnv.require(conv, "schedule_appointment")
    if gate:
        return gate

    conv.write_metric("MAKE_APPOINTMENT_FLOW_INITIATED", write_once=True)
    flow.goto_step("Schedule Visit", "caller verified")
    existing = visits.upcoming_visits(conv)
    note = ""
    if existing:
        note = (
            f"They already have {visits.describe_visit(existing[0], conv)}. Don't bring it up "
            "unless they seem to mean that visit."
        )
    return (
        "Help the caller book a visit. If they have already said what the problem is or where it "
        "is, call update_visit_request with it now; if they have said when suits, call "
        "find_visit_time with it now. Otherwise ask what the problem is. "
        f"{note}\n\n{request_state(conv)}"
    )
