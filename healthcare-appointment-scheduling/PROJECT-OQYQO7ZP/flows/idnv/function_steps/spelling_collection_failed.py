from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


def spelling_collection_failed(conv: Conversation, flow: Flow):
    """Hand off when the caller refuses or cannot spell their name."""
    return handoff(
        conv,
        reason="IDNV_SPELLING_COLLECTION_FAILED",
        utterance="No problem — let me transfer you to someone who can help.",
    )
