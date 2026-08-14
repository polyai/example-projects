import re
from collections.abc import Iterator

from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call
from functions.utterances import utterance


class ActionsIterator:
    def __init__(self, identifier: str, actions: list[str]):
        self.actions = actions
        self.identifier = identifier

    def get_next(self, conv) -> str:
        if self.identifier in conv.state and conv.state[self.identifier] is not None:
            conv.state[self.identifier] += 1
        else:
            conv.state[self.identifier] = 0

        if conv.state[self.identifier] == len(self.actions):
            return transfer_call(
                conv,
                "DEFAULT",
                "IDNV_FAILED",
                utterance(conv, "idnv_transfer_default"),
            )

        return self.actions[conv.state[self.identifier]]


DIGIT_ASR_CORRECTIONS = {
    "1": {r"\bone\b", r"\bon\b", r"\bun\b", r"\bune\b"},
    "2": {r"\btwo\b", r"\bdeux\b"},
    "3": {r"\bthree\b", r"\btrois\b"},
    "4": {r"\bfour\b", r"\bquatre\b"},
    "5": {r"\bfive\b", r"\bfi\b", r"\bfve\b", r"\bcinq\b"},
    "6": {r"\bsix\b"},
    "7": {r"\bseven\b", r"\bsept\b"},
    "8": {r"\beight\b", r"\bat\b", "x", r"\bhuit\b"},
    "9": {r"\bnine\b", r"\bneuf\b"},
    "0": {r"\bzero\b", r"\bzoo\b", r"\bzéro\b"},
}

LETTER_ASR_CORRECTIONS = {
    "N": {r"\band\b"},
    "M": {r"\bem\b"},
    "S": {r"\bess\b"},
    "F": {r"\beff\b"},
}


def invert_list_dict(list_dict) -> dict:
    """invert a dict with list values"""
    return {value: key for key, values in list_dict.items() for value in values}


def try_alternative_transcripts(
    conv: Conversation, digits: int, max_digits: int | None = None
) -> Iterator[str]:
    """
    Match all number with `digits` count but not more than `max_digits`. By default, max_digits == digits
    """
    if max_digits is None:
        max_digits = digits
    pattern = re.compile(rf"\b(?:\d[\s\.\-]*){{{digits},{max_digits}}}\b")
    for transcript in conv.transcript_alternatives:
        cleaned = re.sub(
            r"(?<=\d)\s+(?=\d)", "", transcript
        )  # remove space between digits
        print(">>>>1", cleaned)
        yield from pattern.findall(cleaned)

        # Try again, but this time with ASR digit correction
        text = transcript
        for incorrect, correct in invert_list_dict(DIGIT_ASR_CORRECTIONS).items():
            text = re.sub(incorrect, correct, text, flags=re.IGNORECASE)
        cleaned_text = re.sub(
            r"(?<=\d)\s+(?=\d)", "", text
        )  # remove space between digits
        print(">>>>2", cleaned_text)
        yield from pattern.findall(cleaned_text)


def try_alternative_postal_transcripts(conv: Conversation) -> Iterator[str]:
    """
    Try to extract a Canadian postal code (ANA NAN format) from alternative transcripts.
    Matches patterns like 'K1A 0A9', 'K1A0A9'.
    """
    pattern = re.compile(r"\b([A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d)\b")
    for transcript in conv.transcript_alternatives:
        for match in pattern.finditer(transcript):
            yield match.group(1)

        text = transcript
        for incorrect, correct in invert_list_dict(DIGIT_ASR_CORRECTIONS).items():
            text = re.sub(incorrect, correct, text, flags=re.IGNORECASE)
        for incorrect, correct in invert_list_dict(LETTER_ASR_CORRECTIONS).items():
            text = re.sub(incorrect, correct, text, flags=re.IGNORECASE)
        if text != transcript:
            for match in pattern.finditer(text):
                yield match.group(1)


def get_bullet_points(*args):
    return "\n".join(f"- {arg}" for arg in args)


@func_description("Transition to step enter_your_step_name")
def idnv_utils(conv: Conversation, flow: Flow):
    pass
