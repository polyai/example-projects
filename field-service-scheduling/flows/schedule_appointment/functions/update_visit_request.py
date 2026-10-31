import re

from _gen import *  # <AUTO GENERATED>
from functions import api_client, idnv, visits
from functions.handoff import handoff

READBACK_KEY = "booking"

_INDOOR_WORDS = (
    "kitchen", "bathroom", "bedroom", "basement", "attic", "living room", "laundry", "inside",
    "indoor", "interior", "sink", "toilet", "shower", "hallway", "closet", "dining", "loft",
)  # fmt: skip
_OUTDOOR_WORDS = (
    "yard", "garden", "lawn", "roof", "gutter", "driveway", "patio", "deck", "porch", "fence",
    "outside", "outdoor", "exterior", "shed", "pool",
)  # fmt: skip


def visit_request(conv) -> dict:
    req = conv.state.visit_request
    if not isinstance(req, dict):
        req = {
            "issue": "",
            "service_type": "",
            "location": "",
            "indoor": None,
            "preferred_date": "",
            "time_of_day": "any",
            "notes": "",
            "offer": None,
            "rejected": 0,
        }
    return dict(req)


def _guess_indoor(location: str):
    text = (location or "").lower()
    if any(re.search(rf"\b{w}\b", text) for w in _OUTDOOR_WORDS):
        return False
    if any(re.search(rf"\b{w}\b", text) for w in _INDOOR_WORDS):
        return True
    return None


def missing_details(req: dict) -> list[str]:
    missing = []
    if not req["issue"]:
        missing.append("what issue they're having")
    if not req["location"]:
        missing.append("where the problem is")
    elif req["indoor"] is None:
        missing.append("whether it's inside or outside")
    if not req["preferred_date"]:
        missing.append("when would suit them")
    return missing


def booking_fields(conv, req: dict) -> list[tuple[str, str]]:
    offer = req.get("offer") or {}
    """What the caller says yes to: the kind of visit and the window. The problem, the place
    and any note are the caller's own words; the visit prep is given once it's booked."""
    return [
        ("visit", f"a {req['service_type'] or 'General Service'} visit"),
        ("when", visits.say_slot(offer, visits.today(conv)) if offer else ""),
    ]


def booking_question(conv, req: dict) -> str:
    offer = req.get("offer") or {}
    day = visits.say_date(offer["date"], visits.today(conv)) if offer else "that day"
    return f"book the visit for {day}"


def request_state(conv) -> str:
    req = visit_request(conv)
    offer = req.get("offer")
    lines = [
        "Problem: " + (req["issue"] or "not given"),
        "Service type: " + (req["service_type"] or "General Service (default)"),
        "Where: "
        + (req["location"] or "not given")
        + (
            ""
            if req["indoor"] is None
            else (" (indoors)" if req["indoor"] else " (outdoors)")
        ),
        "When suits: "
        + (req["preferred_date"] or "not given")
        + ("" if req["time_of_day"] == "any" else f", {req['time_of_day']}"),
        "Offered: "
        + (visits.say_window(offer, visits.today(conv)) if offer else "nothing yet"),
    ]
    missing = missing_details(req)
    if missing:
        nxt = f"Ask for {missing[0]}."
    elif offer:
        nxt = "Wait for the caller's yes or no to booking the offered window."
    else:
        nxt = "Call find_visit_time to get a window to offer."
    return visits.call_state(conv, ["Task: book a new visit"] + lines, nxt)


def offer_next(conv, req: dict, rejected: bool, preference_changed: bool):
    """Shared by update_visit_request and find_visit_time: save the request, ask for what is
    missing, or offer a window (a new one when the caller turned the last one down or changed
    when suits) and say what to read back."""
    after = None
    if rejected and req["offer"]:
        req["rejected"] += 1
        conv.write_metric("OFFERED_SLOT_REJECTED")
        if req["rejected"] >= visits.MAX_REJECTED_OFFERS:
            conv.state.visit_request = req
            return handoff(
                conv,
                "OFFERED_APPOINTMENT_SLOT_REJECTED",
                "I'm sorry I couldn't find a time that suits. Let me put you through to our "
                "scheduling team, one moment please.",
                "CUSTOMER_CARE",
            )
        after = req["offer"]

    missing = missing_details(req)
    if missing:
        conv.state.visit_request = req
        tool = (
            "find_visit_time"
            if missing[0] == "when would suit them"
            else "update_visit_request"
        )
        return (
            f"Saved. Still needed: {missing[0]}. If the caller has already said it, call {tool} "
            f"with it now; otherwise ask for it.\n\n{request_state(conv)}"
        )

    note = ""
    if rejected or preference_changed or not req["offer"]:
        window, note = visits.find_window(
            conv, req["preferred_date"], req["time_of_day"], after
        )
        if window is None:
            conv.state.visit_request = req
            return handoff(
                conv,
                "NO_AVAILABILITY_FOUND",
                "I'm sorry, I can't see any open times in the next two weeks. Let me put you "
                "through to our scheduling team, one moment please.",
                "CUSTOMER_CARE",
            )
        req["offer"] = window
    conv.state.visit_request = req
    conv.write_metric("SLOT_OFFERED")

    text, mode = visits.readback_text(conv, READBACK_KEY, booking_fields(conv, req))
    if mode == "none":
        return (
            "Nothing has changed since the readback. If the caller's latest reply was a clear yes "
            "to booking it, call make_new_appointment with caller_confirmed='true'; otherwise "
            f"{visits.yes_no_question(booking_question(conv, req), 'ask')}\n\n{request_state(conv)}"
        )
    lead = "Offer this" if mode == "full" else "Tell the caller only what changed"
    say = visits.read_back_and_ask(lead, text, "book it")
    return f"{note + ' ' if note else ''}{say}\n\n{request_state(conv)}"


def check_open(conv):
    """The refusal both request tools share, or None when the request can be updated."""
    if not idnv.is_verified(conv):
        return idnv.require(conv, "schedule_appointment")
    if conv.state.booked_appointment_id:
        return (
            "ALREADY BOOKED - do not call this again for it. If the caller wants to change it, "
            "call start_reschedule_appointment."
        )
    return None


@func_description(
    "Save what the visit is for: the problem, the service type, where it is and any note for the technician. Call it whenever the caller gives or changes any of these. When the caller has also said when suits, it offers a window."
)
@func_parameter(
    "issue", "The problem in the caller's words, e.g. 'leak under the kitchen sink'."
)
@func_parameter(
    "service_type",
    "One of: General Service, Deep Clean, Emergency Repair, Maintenance Check. Use General Service when the caller isn't sure. Empty if nothing has been said about the problem.",
)
@func_parameter(
    "location", "Where the problem is, e.g. 'kitchen', 'back yard'. Empty if not said."
)
@func_parameter(
    "indoor_or_outdoor",
    "'indoor' or 'outdoor' if the caller said so or it is obvious from the location; else empty.",
)
@func_parameter("notes", "Anything they want the technician to know. Empty if none.")
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me see what we have.", 3), ("One more moment.", 3)],
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
        req["indoor"] = _guess_indoor(req["location"])
    side = str(indoor_or_outdoor or "").strip().lower()
    if side in ("indoor", "outdoor"):
        req["indoor"] = side == "indoor"
    elif req["location"] and req["indoor"] is None:
        req["indoor"] = _guess_indoor(req["issue"])
    note_text = str(notes or "").strip()
    if note_text and note_text.lower() not in ("na", "none", "no"):
        req["notes"] = note_text
    return offer_next(conv, req, rejected=False, preference_changed=False)
