from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


def name_collection_failed(conv: Conversation, flow: Flow):
    """Hand off when the user refuses or cannot provide their name."""
    return handoff(
        conv,
        reason="IDNV_COLLECTION_FAILED",
        utterance="No problem — let me transfer you to someone who can help.",
    )
