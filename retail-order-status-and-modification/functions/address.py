"""US delivery addresses: parsing what the caller said, what's missing, and the readback.

Held in code:
- an address needs a house or building number, a street and a five-digit ZIP code; a
  missing ZIP or house number is asked for on its own and isn't a miss;
- the readback says the house number digit by digit (a round number like 100 as "one
  hundred"), unit letters spelled ("three B"), the state in full (from the ZIP when the
  caller didn't say it) and the ZIP digit by digit;
- a later answer that is only a ZIP, only a house number, or a correction to part of the
  address is merged with what the caller said before.
"""

import re

from _gen import *  # <AUTO GENERATED>

FIELDS = ("number", "street", "unit", "city", "state", "zip")

STREET_TYPES = {
    "street": "Street", "st": "Street", "avenue": "Avenue", "ave": "Avenue", "av": "Avenue",
    "drive": "Drive", "dr": "Drive", "road": "Road", "rd": "Road", "boulevard": "Boulevard",
    "blvd": "Boulevard", "lane": "Lane", "ln": "Lane", "way": "Way", "court": "Court",
    "ct": "Court", "place": "Place", "pl": "Place", "terrace": "Terrace", "parkway": "Parkway",
    "pkwy": "Parkway", "circle": "Circle", "highway": "Highway", "hwy": "Highway",
    "square": "Square", "trail": "Trail", "plaza": "Plaza", "alley": "Alley", "row": "Row",
}  # fmt: skip
UNIT_WORDS = {
    "apartment": "apartment", "apt": "apartment", "unit": "unit", "suite": "suite",
    "ste": "suite", "floor": "floor", "fl": "floor", "#": "unit", "number": "unit",
}  # fmt: skip
STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "Washington D.C.",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "PR": "Puerto Rico",
}  # fmt: skip
_STATE_NAMES = {v.lower(): k for k, v in STATES.items()}
# First three digits of the ZIP code -> state (USPS prefix ranges).
_ZIP3 = [
    (5, 5, "NY"), (6, 9, "PR"), (10, 27, "MA"), (28, 29, "RI"), (30, 38, "NH"), (39, 49, "ME"),
    (50, 54, "VT"), (55, 55, "MA"), (56, 59, "VT"), (60, 69, "CT"), (70, 89, "NJ"),
    (100, 149, "NY"), (150, 196, "PA"), (197, 199, "DE"), (200, 205, "DC"), (206, 219, "MD"),
    (220, 246, "VA"), (247, 268, "WV"), (270, 289, "NC"), (290, 299, "SC"), (300, 319, "GA"),
    (320, 349, "FL"), (350, 369, "AL"), (370, 385, "TN"), (386, 397, "MS"), (398, 399, "GA"),
    (400, 427, "KY"), (430, 459, "OH"), (460, 479, "IN"), (480, 499, "MI"), (500, 528, "IA"),
    (530, 549, "WI"), (550, 567, "MN"), (569, 569, "DC"), (570, 577, "SD"), (580, 588, "ND"),
    (590, 599, "MT"), (600, 629, "IL"), (630, 658, "MO"), (660, 679, "KS"), (680, 693, "NE"),
    (700, 714, "LA"), (716, 729, "AR"), (730, 749, "OK"), (750, 799, "TX"), (800, 816, "CO"),
    (820, 831, "WY"), (832, 838, "ID"), (840, 847, "UT"), (850, 865, "AZ"), (870, 884, "NM"),
    (885, 885, "TX"), (889, 898, "NV"), (900, 961, "CA"), (967, 968, "HI"), (970, 979, "OR"),
    (980, 994, "WA"), (995, 999, "AK"),
]  # fmt: skip
_DIGIT_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
_SMALL = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["_", "_", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


@func_description("[UTIL] Delivery address helpers, not callable directly")
def address(conv: Conversation):
    return "Address helpers module."


def state_from_zip(zip_code: str) -> str:
    if not re.fullmatch(r"\d{5}", zip_code or ""):
        return ""
    prefix = int(zip_code[:3])
    return next((st for lo, hi, st in _ZIP3 if lo <= prefix <= hi), "")


def _title(text: str) -> str:
    return " ".join(
        w if w.isupper() and len(w) > 1 else w.capitalize() for w in text.split()
    )


def _street(text: str) -> str:
    words = [w for w in re.split(r"\s+", text.strip().strip(".")) if w]
    out = []
    for i, w in enumerate(words):
        key = w.lower().strip(".")
        out.append(
            STREET_TYPES.get(key, w.capitalize())
            if i == len(words) - 1
            else w.capitalize()
        )
    return " ".join(out)


def _state_code(text: str) -> str:
    t = text.strip().strip(".")
    if t.upper() in STATES and len(t) == 2:
        return t.upper()
    return _STATE_NAMES.get(t.lower(), "")


def parse(text: str) -> dict:
    """What the caller said, split into number, street, unit, city, state (two letters) and
    zip. Parts that weren't said are ''."""
    out = dict.fromkeys(FIELDS, "")
    t = " ".join(str(text or "").replace("\n", " ").split())
    if not t:
        return out
    zips = [
        m
        for m in re.finditer(r"\b(\d{5})(?:-\d{4})?\b", t)
        if m.start() > 0 or len(t) <= 10
    ]
    if zips:
        m = zips[-1]
        out["zip"] = m.group(1)
        t = (t[: m.start()] + t[m.end() :]).strip(" ,")
    m = re.search(
        r"(?:,\s*|\s)(apartment|apt|unit|suite|ste|floor|fl|#)\.?\s*#?\s*([A-Za-z0-9-]+)\b",
        t,
        re.IGNORECASE,
    )
    if m:
        out["unit"] = f"{UNIT_WORDS[m.group(1).lower()]} {m.group(2).upper()}"
        t = (t[: m.start()] + t[m.end() :]).strip(" ,")
    m = re.match(r"\s*(\d+[A-Za-z]?)\b\s*", t)
    if m:
        out["number"] = m.group(1).upper()
        t = t[m.end() :].strip(" ,")
    parts = [p.strip() for p in t.split(",") if p.strip()]
    if not parts:
        return out
    if len(parts) == 1:
        words = parts[0].split()
        idx = next(
            (i for i, w in enumerate(words) if w.lower().strip(".") in STREET_TYPES),
            None,
        )
        street = words[: idx + 1] if idx is not None else words
        rest = words[idx + 1 :] if idx is not None else []
        parts = [" ".join(street)] + ([" ".join(rest)] if rest else [])
    out["street"] = _street(parts[0]) if re.search(r"[A-Za-z]", parts[0]) else ""
    rest = parts[1:]
    if rest:
        code = _state_code(rest[-1])
        if code and len(rest) >= 2:
            out["state"], rest = code, rest[:-1]
        elif len(rest) == 1:
            words = rest[0].split()
            if len(words) > 1 and _state_code(words[-1]) and len(words[-1]) == 2:
                out["state"], rest = _state_code(words[-1]), [" ".join(words[:-1])]
        out["city"] = _title(", ".join(rest))
    return out


def merge(before: dict | None, said: dict) -> dict:
    """A later answer on top of the address so far: a ZIP or a house number on its own fills
    that part; a correction keeps the parts it doesn't mention."""
    before = dict(before or dict.fromkeys(FIELDS, ""))
    if not any(said.values()):
        return before
    if not said["street"]:
        merged = dict(before)
        for k in ("number", "unit", "zip", "state", "city"):
            if said[k]:
                merged[k] = said[k]
        if said["zip"] and not said["state"]:
            merged["state"] = state_from_zip(said["zip"]) or merged["state"]
        return merged
    merged = dict(said)
    if not (said["city"] or said["zip"]):
        for k in ("city", "state", "zip"):
            merged[k] = before[k]
        if not said["unit"]:
            merged["unit"] = before["unit"]
    # "54 Elm" for "Elm Street": keep the street type they said before.
    if before["street"] and before["street"].lower().startswith(
        said["street"].lower() + " "
    ):
        merged["street"] = before["street"]
    if merged["zip"] and not merged["state"]:
        merged["state"] = state_from_zip(merged["zip"])
    return merged


def recognisable(said: dict) -> bool:
    """Whether an answer can be made out as (part of) an address: a house number, a ZIP code,
    or a street with a street type ("Elm Street")."""
    street_type = said["street"].split(" ")[-1] if said["street"] else ""
    return bool(said["number"] or said["zip"] or street_type in STREET_TYPES.values())


def missing(addr: dict) -> str:
    """'' when the address is complete; else 'street', 'zip' or 'number'."""
    if not addr.get("street"):
        return "street"
    if not addr.get("zip"):
        return "zip"
    if not addr.get("number"):
        return "number"
    return ""


def _under_hundred(n: int) -> str:
    if n < 20:
        return _SMALL[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f"-{_SMALL[ones]}" if ones else "")


def say_number(value: str) -> str:
    """'45' -> 'four five'; '100' -> 'one hundred'; '12B' -> 'one two B'."""
    m = re.fullmatch(r"(\d+)([A-Za-z]?)", value or "")
    if not m:
        return value
    digits, letter = m.groups()
    n = int(digits)
    if not letter and n % 100 == 0 and 0 < n < 10000:
        if n % 1000 == 0:
            words = f"{_SMALL[n // 1000]} thousand"
        else:
            words = f"{_under_hundred(n // 100)} hundred"
    else:
        words = " ".join(_DIGIT_WORDS[int(d)] for d in digits)
    return words + (f" {letter.upper()}" if letter else "")


def say_unit(unit: str) -> str:
    """'apartment 3B' -> 'apartment three B'."""
    label, _, value = unit.partition(" ")
    spelled = " ".join(
        _DIGIT_WORDS[int(c)] if c.isdigit() else c.upper() for c in value if c.isalnum()
    )
    return f"{label} {spelled}".strip()


def say_zip(zip_code: str) -> str:
    return " ".join(_DIGIT_WORDS[int(d)] for d in zip_code)


def spoken_parts(addr: dict) -> dict:
    """The readback, part by part, as it is spoken."""
    state = STATES.get(addr.get("state") or state_from_zip(addr.get("zip", "")), "")
    street = " ".join(x for x in (say_number(addr["number"]), addr["street"]) if x)
    return {
        "street": ", ".join(
            x for x in (street, say_unit(addr["unit"]) if addr["unit"] else "") if x
        ),
        "place": ", ".join(x for x in (addr["city"], state) if x),
        "zip": say_zip(addr["zip"]) if addr["zip"] else "",
    }


def readback_fields(addr: dict) -> list[tuple[str, str]]:
    parts = spoken_parts(addr)
    return [(k, parts[k]) for k in ("street", "place", "zip")]


def spoken(addr: dict, only: list[str] | None = None) -> str:
    parts = spoken_parts(addr)
    keys = [
        k
        for k in ("street", "place", "zip")
        if parts[k] and (only is None or k in only)
    ]
    return ", ".join(parts[k] for k in keys)


def formatted(addr: dict) -> str:
    """'45 Elm Street, Apartment 3B, New York, NY 10002' for the order system."""
    state = addr.get("state") or state_from_zip(addr.get("zip", ""))
    line = " ".join(x for x in (addr["number"], addr["street"]) if x)
    unit = addr["unit"][:1].upper() + addr["unit"][1:] if addr["unit"] else ""
    tail = " ".join(x for x in (state, addr["zip"]) if x)
    return ", ".join(x for x in (line, unit, addr["city"], tail) if x)
