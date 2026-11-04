from _gen import *  # <AUTO GENERATED>
from functions import billing

CSAT_QUESTION = (
    "Before you go, would you mind answering two quick questions about today's call?"
)


def goodbye(conv) -> str:
    if conv.state.paid_this_call:
        return "Thanks for calling, and thanks for your payment. Have a good day!"
    company = (
        (getattr(conv.variant, "site_name", "") or "").strip() if conv.variant else ""
    )
    return (
        f"Thanks for calling {company}. Have a good day!"
        if company
        else "Thanks for calling. Have a good day!"
    )


@func_description(
    "[Agent Behaviour] Say goodbye and end the call, only once the caller has said they don't need anything else."
)
def goodbye_and_hangup(conv: Conversation):
    # A line said in this same turn that must be heard (a confirmation number) is said again
    # first, so the goodbye never replaces it.
    unheard = billing.unheard_line(conv)
    prefix = f"{unheard} " if unheard else ""
    flags = (conv.real_time_config or {}).get("flags", {}) or {}
    if flags.get("csat_enabled") and not conv.state.csat_offered:
        conv.write_metric("CSAT_OFFERED")
        conv.state.csat_offered = True
        conv.goto_flow("CSAT")
        return {"utterance": f"{prefix}{CSAT_QUESTION}"}
    if conv.current_flow == "CSAT":
        conv.write_metric("CSAT_REFUSED")
        return {"utterance": f"No problem. {goodbye(conv)}", "hangup": True}
    return {"utterance": f"{prefix}{goodbye(conv)}", "hangup": True}
