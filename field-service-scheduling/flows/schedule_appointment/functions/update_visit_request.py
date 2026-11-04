import re

from _gen import *  # <AUTO GENERATED>
from functions import api_client, idnv, visits

READBACK_KEY = "booking"
LOOKUP_KEY = "booking"

ASK_PROBLEM = "What's going on? What do you need the technician for?"
ASK_WHERE = "And is that inside the house or outside?"
ASK_WHEN_REPAIR = "Would you like the earliest we've got, or is there a particular day that suits you?"
ASK_WHEN_ROUTINE = "What day would suit you?"
ROUTINE_TYPES = ("Maintenance Check", "Deep Clean")

_INDOOR_WORDS = (
    "kitchen", "bathroom", "bedroom", "basement", "attic", "living room", "laundry", "inside",
    "indoor", "indoors", "interior", "sink", "toilet", "shower", "bath", "tub", "hallway",
    "closet", "dining", "loft", "garage", "upstairs", "downstairs", "ceiling", "dishwasher",
    "disposal", "water heater", "furnace", "boiler", "washer", "dryer", "oven", "stove",
    "fridge", "refrigerator", "outlet", "thermostat", "ac", "air conditioning", "heating",
    "faucet", "drain", "pipe",
)  # fmt: skip
_OUTDOOR_WORDS = (
    "yard", "garden", "lawn", "roof", "gutter", "gutters", "driveway", "patio", "deck", "porch",
    "fence", "outside", "outdoor", "outdoors", "exterior", "shed", "pool", "sprinkler",
)  # fmt: skip


def visit_request(conv) -> dict:
    req = conv.state.visit_request
    if not isinstance(req, dict):
        req = {
            "issue": "",
            "service_type": "",
            "location": "",
            "indoor": None,
            "notes": "",
        }
    return dict(req)


def guess_indoor(*texts: str):
    """True or False when the words make it obvious, else None (the agent asks)."""
    text = " ".join(t or "" for t in texts).lower()
    if any(re.search(rf"\b{w}\b", text) for w in _OUTDOOR_WORDS):
        return False
    if any(re.search(rf"\b{w}\b", text) for w in _INDOOR_WORDS):
        return True
    return None


def issue_phrase(issue: str) -> str:
    """The problem as it follows "for": 'the leak under your sink', 'your AC tune-up'."""
    text = re.sub(r"\s+", " ", (issue or "").strip().rstrip("."))
    if not text:
        return ""
    # "the dishwasher won't drain" -> "the dishwasher": keep the thing, drop the verb clause.
    text = re.split(
        r"\s+(?:won'?t|isn'?t|is not|not|doesn'?t|does not|keeps|is|are|has|have|stopped|"
        r"died|broke|quit|went)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    text = re.sub(r"^(my|our)\b", "your", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(my|our)\b", "your", text, flags=re.IGNORECASE)
    if not re.match(r"(the|your|a|an|some)\b", text, flags=re.IGNORECASE):
        text = f"the {text}"
    return text[0].lower() + text[1:]


def missing_detail(req: dict) -> str:
    """The next thing to ask for, in the design's words, or "" when the request is complete."""
    if not req["issue"]:
        return ASK_PROBLEM
    if req["indoor"] is None:
        return ASK_WHERE
    return ""


def when_question(req: dict) -> str:
    return ASK_WHEN_ROUTINE if req["service_type"] in ROUTINE_TYPES else ASK_WHEN_REPAIR


def booking_fields(conv, req: dict, window: dict | None) -> list[tuple[str, str]]:
    """What the caller says yes to: the problem in their words, the day, the window and the
    address on the account (never read out)."""
    now = visits.today(conv)
    return [
        ("problem", issue_phrase(req["issue"])),
        ("day", visits.on_day(window["date"], now) if window else ""),
        ("window", visits.between(window) if window else ""),
        ("address", "at the address on your account"),
    ]


def booking_readback(conv, req: dict, window: dict, only: dict | None = None) -> str:
    """The readback sentence and the question. `only` holds the changed fields after a
    correction: then only those are said (with the day, when the window changed)."""
    f = dict(booking_fields(conv, req, window))
    if only is None:
        return (
            f"So that's for {f['problem']} {f['day']}, arriving {f['window']}, {f['address']}. "
            "Shall I book that?"
        )

    parts = []
    if "problem" in only:
        parts.append(f["problem"])
    if "day" in only or "window" in only:
        parts.append(f"arriving {f['window']} {f['day']}")
    return f"So that's {', '.join(parts)}. Shall I book that?"


def first_readback(conv, req: dict, window: dict) -> str:
    """The first readback. Called in the same turn as the lookup, it starts with the
    availability line and leaves out what that line has just said."""
    hello = visits.thanks(conv)
    lead = visits.lead_line(conv, LOOKUP_KEY, window)
    if not lead:
        return hello + booking_readback(conv, req, window)
    f = dict(booking_fields(conv, req, window))
    day = "" if lead.startswith("The earliest") else f" {f['day']}"
    return f"{hello}{lead} So that's for {f['problem']}{day}, {f['address']}. Shall I book that?"


def request_state(conv) -> str:
    req = visit_request(conv)
    windows = visits.looked_up(conv, LOOKUP_KEY)
    lines = [
        "Task: book a new visit",
        "Problem: " + (req["issue"] or "not given"),
        "Service type: " + (req["service_type"] or "General Service (default)"),
        "Inside or outside: "
        + (
            "not known"
            if req["indoor"] is None
            else ("inside" if req["indoor"] else "outside")
        ),
        f"Windows looked up: {len(windows)}"
        if windows
        else "Windows looked up: none yet",
    ]
    missing = missing_detail(req)
    if missing:
        nxt = f'Ask: "{missing}"'
    elif not windows:
        nxt = (
            "Ask when suits them, unless they've said: for a repair or estimate, "
            f'"{ASK_WHEN_REPAIR}"; for routine maintenance or a clean, "{ASK_WHEN_ROUTINE}" '
            "Then call find_visit_time with their answer."
        )
    else:
        nxt = "Offer windows from the latest find_visit_time response, then call make_new_appointment with the one they choose."
    return visits.call_state(conv, lines, nxt)


def check_open(conv):
    """The refusal every booking tool shares, or None when the request can be updated."""
    if not idnv.is_verified(conv):
        return idnv.require(conv, "schedule_appointment")
    if conv.state.booked_appointment_id:
        return (
            "ALREADY BOOKED - do not book it again. If the caller wants to change it, call "
            "start_reschedule_appointment; for another visit, start_make_appointment."
        )
    return None


@func_description(
    "Save what the visit is for: the problem, the service type, whether it's inside or outside and any note for the technician. Call it whenever the caller gives or changes any of these."
)
@func_parameter(
    "issue",
    "The problem as a short noun phrase in the caller's own words, as it would follow 'for' in a readback: 'the leak under your sink', 'the dishwasher', 'your AC tune-up'. Never a verb phrase. Empty if not said.",
)
@func_parameter(
    "service_type",
    "One of: General Service, Deep Clean, Emergency Repair, Maintenance Check. Use General Service for a repair or when unsure, Maintenance Check for a tune-up or routine service. Empty if nothing has been said about the problem.",
)
@func_parameter(
    "location", "Where the problem is, e.g. 'kitchen', 'garage'. Empty if not said."
)
@func_parameter(
    "indoor_or_outdoor",
    "'indoor' or 'outdoor' if the caller said so or it's obvious from the problem (a sink is indoors, gutters are outdoors); else empty.",
)
@func_parameter(
    "notes", "Anything the caller offers for the technician to know. Empty if none."
)
def update_visit_request(
    conv: Conversation,
    flow: Flow,
    issue: str,
    service_type: str,
    location: str,
    indoor_or_outdoor: str,
    notes: str,
):
    refusal = check_open(conv)
    if refusal:
        return refusal

    req = visit_request(conv)
    if str(issue or "").strip():
        req["issue"] = issue.strip()
    catalog = api_client.service_types(conv)
    wanted_type = str(service_type or "").strip().lower()
    chosen = next((s for s in catalog if s.lower() == wanted_type), "")
    if chosen:
        req["service_type"] = chosen
    elif req["issue"] and not req["service_type"]:
        req["service_type"] = "General Service"
    if str(location or "").strip():
        req["location"] = location.strip()
    side = str(indoor_or_outdoor or "").strip().lower()
    if side in ("indoor", "outdoor", "inside", "outside"):
        req["indoor"] = side in ("indoor", "inside")
    elif req["indoor"] is None:
        req["indoor"] = guess_indoor(req["location"], req["issue"])
    note_text = str(notes or "").strip()
    if note_text and note_text.lower() not in ("na", "none", "no"):
        req["notes"] = note_text
    conv.state.visit_request = req

    missing = missing_detail(req)
    if missing:
        return f'Saved. Ask: "{missing}"\n\n{request_state(conv)}'
    if visits.looked_up(conv, LOOKUP_KEY):
        return (
            "Saved. If a window has been chosen, call make_new_appointment with it "
            f"(caller_confirmed='false') to read back the change.\n\n{request_state(conv)}"
        )
    said = str(conv.state.day_said or "").strip()
    if said:
        return (
            f"Saved. They've already said when: {said!r}. Call find_visit_time now with "
            f"day_said={said!r}; don't ask when.\n\n{request_state(conv)}"
        )
    return (
        "Saved. If they've already said when suits them, call find_visit_time with it now. "
        f'Otherwise ask: "{when_question(req)}"\n\n{request_state(conv)}'
    )
