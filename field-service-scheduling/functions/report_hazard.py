"""Safety lines, held in code so the wording stays exactly as each client signed it off.

Gas, carbon monoxide and fire end the call after the line, so the caller isn't kept inside on
the phone. An electrical hazard is followed by the emergency team. A medical emergency is told
to hang up and call 911."""

from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff

SAFETY_LINES = {
    "gas": (
        "Please leave the house right away, and once you're outside, call 911 or your gas "
        "company's emergency line. Don't switch anything on or off on your way out."
    ),
    "co_alarm": "Please get everyone out of the house now, and call 911 once you're outside.",
    "fire": "Please get everyone out now and call 911.",
    "electrical": (
        "Please keep everyone away from it, and if you see smoke or flames, leave the house and "
        "call 911. I'll put you through to our emergency team now."
    ),
    "medical": "Please hang up and call 911.",
}
ALIASES = {
    "carbon_monoxide": "co_alarm", "co": "co_alarm", "smoke": "fire", "sparking": "electrical",
    "sparks": "electrical", "burning_smell": "electrical", "water_near_electrics": "electrical",
}  # fmt: skip


@func_description(
    "The caller reports danger: a gas smell, a carbon monoxide alarm, smoke or fire, sparking or a burning smell from an outlet or panel, water near electrics, or a medical emergency. Call it at once, before anything else, even mid-task or while finding their account. Not for a hazard that's already been dealt with."
)
@func_parameter("hazard", "One of: gas, co_alarm, fire, electrical, medical.")
def report_hazard(conv: Conversation, hazard: str):
    key = str(hazard or "").strip().lower().replace(" ", "_").replace("-", "_")
    key = ALIASES.get(key, key)
    if key not in SAFETY_LINES:
        conv.log.warning("Unknown hazard, using the electrical line", hazard=key)
        key = "electrical"
    line = SAFETY_LINES[key]
    conv.write_metric("SAFETY_HAZARD", key)
    conv.state.must_hear = (
        line  # end_call says it again if the call ends in the same turn
    )
    conv.state.task = ""
    if conv.current_flow:
        conv.exit_flow()
    if key == "electrical":
        return handoff(conv, "SAFETY_HAZARD", line, "EMERGENCY")
    return {"utterance": line, "hangup": True}
