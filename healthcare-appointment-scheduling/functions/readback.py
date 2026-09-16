from _gen import *  # <AUTO GENERATED>

DIGIT_WORDS = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}


def digits_only(value) -> str:
    return "".join(c for c in str(value or "") if c in DIGIT_WORDS)


def _groups(digits: str) -> list[str]:
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) == 10:
        return [digits[:3], digits[3:6], digits[6:]]
    return [digits[i : i + 3] for i in range(0, len(digits), 3)]


def spell_digits(value) -> str:
    digits = digits_only(value)
    if not digits:
        return ""
    spoken = [" ".join(DIGIT_WORDS[d] for d in g) for g in _groups(digits)]
    if len(spoken) == 1:
        return spoken[0]
    out = spoken[0]
    for i, group in enumerate(spoken[1:]):
        filler = "and finally" if i == len(spoken) - 2 else "then"
        out += f", {filler} {group}"
    return out


@func_description("[UTIL] Digit readback helpers, not callable directly")
def readback(conv: Conversation):
    pass
